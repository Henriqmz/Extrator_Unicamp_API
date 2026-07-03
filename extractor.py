import fitz
import os
import re
from PIL import Image

def drawing_eh_texto(page, rect, threshold=5.0):
    """Retorna True se o drawing contém majoritariamente texto selecionável."""
    texto = page.get_text("text", clip=rect).strip()
    if not texto:
        return False
    area = rect.width * rect.height
    if area <= 0:
        return False
    densidade = len(texto) / area * 1000
    return densidade > threshold

IMG_REL_PREFIX = "./imgs/"

def linhas_por_coluna(page, mid_x):
    """
    Divide as linhas de texto da página em duas colunas (esquerda, direita),
    mesclando horizontalmente linhas com coordenadas Y muito próximas (< 6.0px)
    para resolver problemas de potências de Física e alternativas em duas colunas.
    Detecta dinamicamente se a página usa layout de coluna única se houver linhas cruzando.
    Retorna (esquerda, direita) onde cada lista contém dicionários com as chaves:
    'texto', 'y', 'bbox'.
    """
    import re
    d = page.get_text("dict")
    
    # 1. Detectar se a página usa layout de coluna única
    total_linhas = 0
    linhas_cruzam = 0
    for b in d["blocks"]:
        if b["type"] == 0:  # Texto
            for line in b["lines"]:
                line_text = "".join(span["text"] for span in line["spans"])
                if not line_text.strip():
                    continue
                total_linhas += 1
                x0, y0, x1, y1 = line["bbox"]
                if x0 < mid_x - 40 and x1 > mid_x + 40:
                    linhas_cruzam += 1
                    
    pct_cruzam = (linhas_cruzam / total_linhas * 100) if total_linhas > 0 else 0
    # Se mais de 12% das linhas cruzam o meio, consideramos layout de coluna única
    layout_coluna_unica = pct_cruzam > 12.0

    raw_lines = {"esquerda": [], "direita": []}
    for b in d["blocks"]:
        if b["type"] == 0:  # Texto
            for line in b["lines"]:
                line_text = "".join(span["text"] for span in line["spans"])
                if not line_text.strip():
                    continue
                x0, y0, x1, y1 = line["bbox"]
                if y0 > page.rect.height * 0.95 and re.match(r"^\d+$", line_text.strip()):
                    continue
                if layout_coluna_unica:
                    col = "esquerda"
                else:
                    centro_x = (x0 + x1) / 2
                    col = "esquerda" if centro_x < mid_x else "direita"
                raw_lines[col].append({
                    "texto": line_text,
                    "y": y0,
                    "x": x0,
                    "bbox": line["bbox"]
                })

    resultado = {"esquerda": [], "direita": []}
    for col in ["esquerda", "direita"]:
        lines = raw_lines[col]
        if not lines:
            continue
        lines.sort(key=lambda x: x["y"])
        
        # Agrupar linhas com Y muito próximo (< 6.0px)
        grouped = []
        for l in lines:
            if not grouped:
                grouped.append([l])
            else:
                ultimo_grupo = grouped[-1]
                media_y = sum(item["y"] for item in ultimo_grupo) / len(ultimo_grupo)
                if abs(l["y"] - media_y) < 6.0:
                    ultimo_grupo.append(l)
                else:
                    grouped.append([l])
                    
        # Concatenar cada grupo ordenando por X
        for g in grouped:
            g.sort(key=lambda x: x["x"])
            texto_completo = ""
            min_x0, min_y0 = g[0]["bbox"][0], g[0]["bbox"][1]
            max_x1, max_y1 = g[0]["bbox"][2], g[0]["bbox"][3]
            
            ultimo_x1 = None
            for item in g:
                txt = item["texto"]
                x0, _, x1, _ = item["bbox"]
                
                if ultimo_x1 is not None and x0 - ultimo_x1 > 15.0:
                    texto_completo += "\n" + txt
                else:
                    if txt.startswith("\t") or txt.startswith(" ") or texto_completo.endswith("\t") or texto_completo.endswith(" "):
                        texto_completo += txt
                    else:
                        texto_completo += " " + txt if texto_completo else txt
                
                ultimo_x1 = x1
                min_x0 = min(min_x0, x0)
                min_y0 = min(min_y0, item["bbox"][1])
                max_x1 = max(max_x1, x1)
                max_y1 = max(max_y1, item["bbox"][3])
            
            texto_completo = re.sub(r' {2,}', ' ', texto_completo).strip()
            
            resultado[col].append({
                "texto": texto_completo,
                "y": g[0]["y"],
                "bbox": [min_x0, min_y0, max_x1, max_y1]
            })
            
    return resultado["esquerda"], resultado["direita"]

def encontrar_labels_alternativas(page, mid_x):
    """
    Retorna as posições X, Y de labels de alternativas ('a)', 'b)', etc.)
    organizadas por coluna: {'esquerda': [(x, y, letra)], 'direita': [(x, y, letra)]}
    """
    labels = {"esquerda": [], "direita": []}
    d = page.get_text("dict")
    for b in d["blocks"]:
        if b["type"] == 0:  # Texto
            for line in b["lines"]:
                line_text = "".join(span["text"] for span in line["spans"]).strip()
                match = re.match(r"^([a-e])\)\s*", line_text.lower())
                if match:
                    letra = match.group(1)
                    x0, y0, x1, y1 = line["bbox"]
                    centro_x = (x0 + x1) / 2
                    col = "esquerda" if centro_x < mid_x else "direita"
                    labels[col].append((x0, y0, letra))
    for col in labels:
        labels[col].sort(key=lambda x: (x[1], x[0]))
    return labels

def map_image(img_y, img_x, mid_x, labels, img_w=None, page=None):
    """
    Retorna a letra da alternativa associada à imagem (ou 'enunciado' se estiver acima).
    Suporta alternativas em colunas paralelas usando distância horizontal e validação de contexto vertical.
    """
    col = "esquerda" if img_x < mid_x else "direita"
    col_labels = labels[col]
    if not col_labels:
        return "enunciado"
        
    min_dx = min(abs(lx - img_x) for lx, ly, letra in col_labels)
    candidates = [c for c in col_labels if abs(c[0] - img_x) <= min_dx + 40]
    
    if not candidates:
        return "enunciado"
        
    y_a = None
    for lx, ly, letra in candidates:
        if letra == 'a':
            y_a = ly
            break
    if y_a is None:
        y_a = candidates[0][1]
        
    if img_y < y_a - 20:
        return "enunciado"
        
    # Filtrar candidatos que estão dentro do limite vertical aceitável (entre ly-20 e ly+150)
    valid_candidates = []
    for lx, ly, letra in candidates:
        if ly - 20 <= img_y <= ly + 150:
            # Restrição 2: se houver texto indicando nova questão ou texto comum entre a alternativa e a imagem, ignorar
            if page is not None:
                rect_entre = fitz.Rect(min(lx, img_x), min(ly, img_y), max(lx, img_x) + 200, max(ly, img_y))
                if not rect_entre.is_empty:
                    texto_entre = page.get_text("text", clip=rect_entre).lower()
                    if "questão" in texto_entre or "texto comum" in texto_entre:
                        continue
            valid_candidates.append((lx, ly, letra))
            
    if not valid_candidates:
        return "enunciado"
        
    # Selecionar a alternativa cujo rótulo (label) está mais próximo da imagem verticalmente
    melhor_cand = min(valid_candidates, key=lambda c: abs(c[1] - img_y))
    return melhor_cand[2]

def detectar_padrao_alternativas(elementos, mid_x, labels=None, page=None):
    """
    Detecta se há imagens que parecem alternativas (3+ de tamanhos semelhantes
    dispostas na mesma coluna e abaixo do início das alternativas). Retorna os índices desses elementos.
    """
    por_coluna = {"E": [], "D": []}
    for i, el in enumerate(elementos):
        if el["tipo"] != "raster":
            continue
        rect = el["rect"]
        centro = (rect.x0 + rect.x1) / 2
        col = "E" if centro < mid_x else "D"
        
        if labels is not None:
            letra_mapped = map_image(rect.y0, centro, mid_x, labels, img_w=rect.width, page=page)
            if letra_mapped == "enunciado" or letra_mapped is None:
                continue
            
        por_coluna[col].append((i, el))
        
    indices_individuais = set()
    for col, items in por_coluna.items():
        for i, el in items:
            similar_group = []
            w_el, h_el = el["rect"].width, el["rect"].height
            if w_el <= 0 or h_el <= 0:
                continue
            for j, other_el in items:
                w_other, h_other = other_el["rect"].width, other_el["rect"].height
                if abs(w_other - w_el) / w_el < 0.3 and abs(h_other - h_el) / h_el < 0.3:
                    similar_group.append(j)
            if len(similar_group) >= 3:
                for idx in similar_group:
                    indices_individuais.add(idx)
    return indices_individuais


def extrair_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    paginas = []
    for page_num, page in enumerate(doc):
        paginas.append({
            "numero": page_num,
            "page": page
        })
    return paginas, doc

def extrair_texto(paginas, imagens=None):
    if imagens is None:
        imagens = []
    texto = ""
    imgs_por_pagina = {}
    for img in imagens:
        p = img["pagina"]
        if p not in imgs_por_pagina:
            imgs_por_pagina[p] = []
        imgs_por_pagina[p].append(img)

    for p in paginas:
        page_num = p["numero"]
        page = p["page"]
        page_width = page.rect.width
        mid_x = page_width / 2
        page_imgs = imgs_por_pagina.get(page_num, [])

        elementos_esquerda = []
        elementos_direita = []

        left_lines, right_lines = linhas_por_coluna(page, mid_x)
        for line in left_lines:
            elementos_esquerda.append({
                "tipo": "texto",
                "y": line["y"],
                "conteudo": line["texto"].strip()
            })
        for line in right_lines:
            elementos_direita.append({
                "tipo": "texto",
                "y": line["y"],
                "conteudo": line["texto"].strip()
            })

        labels_pagina = encontrar_labels_alternativas(page, mid_x)

        for img in page_imgs:
            img_x = img.get("x", 0)
            img_y = img["y"]
            img_w = img.get("largura", 0)
            centro_x = img_x + img_w / 2
            coluna_img = "esquerda" if centro_x < mid_x else "direita"
            
            # P2: se a imagem está mapeada para uma alternativa, omitimos a inserção no texto do enunciado
            letra_mapped = map_image(img_y, img_x, mid_x, labels_pagina, img_w=img_w, page=page)
            if letra_mapped is not None and letra_mapped != "enunciado":
                continue

            el_img = {
                "tipo": "imagem",
                "y": img_y,
                "conteudo": f'\n\n![figura]({IMG_REL_PREFIX}{os.path.basename(img["arquivo"])})\n\n'
            }
            if coluna_img == "esquerda":
                elementos_esquerda.append(el_img)
            else:
                elementos_direita.append(el_img)

        elementos_esquerda.sort(key=lambda x: x["y"])
        elementos_direita.sort(key=lambda x: x["y"])

        for el in elementos_esquerda + elementos_direita:
            if el["tipo"] == "texto":
                texto += el["conteudo"] + "\n"
            else:
                texto += el["conteudo"]

    return texto

def gerar_nome(output_dir, prefixo, page_index, tipo, idx, ext):
    pref = f"{prefixo}_" if prefixo else ""
    return os.path.join(output_dir, f"{pref}p{page_index}_{tipo}{idx}.{ext}")

def converter_para_webp(caminho_original: str) -> str:
    """Converte uma imagem para WebP, deleta o original e retorna o novo caminho."""
    caminho_webp = os.path.splitext(caminho_original)[0] + ".webp"
    with Image.open(caminho_original) as img:
        img.save(caminho_webp, "WEBP", quality=85)
    os.remove(caminho_original)
    return caminho_webp

def coluna(rect, mid_x):
    """Classificação de coluna mais restritiva."""
    largura_total = rect.width
    if largura_total <= 0:
        return "E"
    parte_esq = max(0.0, min(mid_x, rect.x1) - rect.x0)
    parte_dir = max(0.0, rect.x1 - max(mid_x, rect.x0))
    if parte_esq > largura_total * 0.2 and parte_dir > largura_total * 0.2:
        return "C"
    centro = (rect.x0 + rect.x1) / 2
    return "E" if centro < mid_x else "D"

def mesma_coluna(r1, r2, mid_x):
    """Elementos só podem ser agrupados se estiverem na mesma coluna (ou cruzando o meio)."""
    c1, c2 = coluna(r1, mid_x), coluna(r2, mid_x)
    if c1 == "C" or c2 == "C":
        return True
    return c1 == c2

def extrair_imagens(doc, output_dir="imgs", prefixo=""):
    os.makedirs(output_dir, exist_ok=True)
    imagens = []

    for page_index, page in enumerate(doc):
        if page_index < 2:
            continue
        page_height = page.rect.height
        margin_top = page_height * 0.1
        margin_bottom = page_height * 0.9

        # 1. Coleta e agrupamento preliminar de desenhos vetoriais (threshold 30px)
        drawings = page.get_drawings()
        rects_vetoriais = []
        for d in drawings:
            r = d["rect"]
            if r.is_empty or r.width < 5 or r.height < 5:
                continue
            if r.y1 <= margin_top or r.y0 >= margin_bottom:
                continue
            rects_vetoriais.append(r)

        grouped_drawings = []
        if rects_vetoriais:
            for r in rects_vetoriais:
                to_merge = []
                for m in grouped_drawings:
                    expanded = fitz.Rect(m.x0 - 30, m.y0 - 30, m.x1 + 30, m.y1 + 30)
                    if expanded.intersects(r):
                        to_merge.append(m)
                if to_merge:
                    union_rect = fitz.Rect(r)
                    for m in to_merge:
                        union_rect = union_rect | m
                        grouped_drawings.remove(m)
                    grouped_drawings.append(union_rect)
                else:
                    grouped_drawings.append(fitz.Rect(r))

        # 2. Coleta de elementos visuais candidatos
        elementos_visuais = []
        imgs_na_pagina = page.get_images(full=True)

        for i, img in enumerate(imgs_na_pagina):
            xref = img[0]
            try:
                base = doc.extract_image(xref)
                if base and (base.get("width", 0) < 10 or base.get("height", 0) < 10):
                    continue
            except Exception:
                continue

            rects = page.get_image_rects(xref)
            if not rects:
                continue
            for r in rects:
                if r.y1 <= margin_top or r.y0 >= margin_bottom:
                    continue
                sobrepoe_desenho = False
                for m in grouped_drawings:
                    if m.width >= 25 and m.height >= 25:
                        intersection = r & m
                        if not intersection.is_empty:
                            overlap_ratio = intersection.get_area() / r.get_area()
                            if overlap_ratio > 0.85:
                                sobrepoe_desenho = True
                                break
                if sobrepoe_desenho:
                    continue
                elementos_visuais.append({
                    "rect": r,
                    "tipo": "raster",
                    "xref": xref,
                    "idx": i,
                    "idx_orig": len(elementos_visuais)
                })

        for idx, m in enumerate(grouped_drawings):
            if m.width >= 25 and m.height >= 25:
                if drawing_eh_texto(page, m):
                    continue  # Pular drawings que são texto
                elementos_visuais.append({
                    "rect": m,
                    "tipo": "drawing",
                    "idx": idx,
                    "idx_orig": len(elementos_visuais)
                })

        # 3. Agrupamento por proximidade (threshold 40px), respeitando colunas
        mid_x = page.rect.width / 2
        labels_pagina = encontrar_labels_alternativas(page, mid_x)
        indices_individuais = detectar_padrao_alternativas(elementos_visuais, mid_x, labels_pagina, page=page)

        grupos = []
        for el in elementos_visuais:
            if el["idx_orig"] in indices_individuais:
                grupos.append([el])
                continue

            grupos_intersetados = []
            for g in grupos:
                contem_individual = any(g_el["idx_orig"] in indices_individuais for g_el in g)
                if contem_individual:
                    continue

                proximo = False
                for g_el in g:
                    if not mesma_coluna(g_el["rect"], el["rect"], mid_x):
                        continue
                    r_expandido = fitz.Rect(
                        g_el["rect"].x0 - 40,
                        g_el["rect"].y0 - 40,
                        g_el["rect"].x1 + 40,
                        g_el["rect"].y1 + 40
                    )
                    if r_expandido.intersects(el["rect"]):
                        proximo = True
                        break
                if proximo:
                    grupos_intersetados.append(g)
            if grupos_intersetados:
                novo_grupo = [el]
                for g in grupos_intersetados:
                    novo_grupo.extend(g)
                    grupos.remove(g)
                grupos.append(novo_grupo)
            else:
                grupos.append([el])

        # Validação pós-agrupamento: desfazer grupos muito largos (largura > 60% da página)
        elementos_para_processar = []
        for g in grupos:
            if len(g) >= 2:
                union_rect = fitz.Rect(g[0]["rect"])
                for el in g[1:]:
                    union_rect = union_rect | el["rect"]
                if union_rect.width > page.rect.width * 0.6:
                    # Desfazer grupo
                    for el in g:
                        elementos_para_processar.append([el])
                else:
                    elementos_para_processar.append(g)
            else:
                elementos_para_processar.append(g)

        # 4. Renderizar e salvar
        group_idx = 0
        for g in elementos_para_processar:
            if not g:
                continue
            if len(g) >= 2:
                union_rect = fitz.Rect(g[0]["rect"])
                for el in g[1:]:
                    union_rect = union_rect | el["rect"]
                padding = 5
                margin_top_context = 10  # P3: Reduzido de 30 para 10
                m_padded = fitz.Rect(
                    max(0, union_rect.x0 - padding),
                    max(0, union_rect.y0 - margin_top_context),
                    min(page.rect.width, union_rect.x1 + padding),
                    min(page.rect.height, union_rect.y1 + padding)
                )
                if m_padded.width <= 0 or m_padded.height <= 0:
                    continue
                nome_temp = gerar_nome(output_dir, prefixo, page_index, "group", group_idx, "png")
                matrix = fitz.Matrix(2, 2)
                pix = page.get_pixmap(clip=m_padded, matrix=matrix)
                if pix.width <= 0 or pix.height <= 0:
                    continue
                pix.save(nome_temp)
                nome_webp = converter_para_webp(nome_temp)
                imagens.append({
                    "pagina": page_index,
                    "y": m_padded.y0,
                    "x": m_padded.x0,
                    "largura": m_padded.width,
                    "arquivo": nome_webp
                })
                group_idx += 1
            else:
                el = g[0]
                if el["tipo"] == "raster":
                    base = doc.extract_image(el["xref"])
                    nome_temp = gerar_nome(output_dir, prefixo, page_index, "img", el["idx"], base["ext"])
                    with open(nome_temp, "wb") as f:
                        f.write(base["image"])
                    nome_webp = converter_para_webp(nome_temp)
                    imagens.append({
                        "pagina": page_index,
                        "y": el["rect"].y0,
                        "x": el["rect"].x0,
                        "largura": el["rect"].width,
                        "arquivo": nome_webp
                    })
                else:
                    padding = 5
                    m = el["rect"]
                    m_padded = fitz.Rect(
                        max(0, m.x0 - padding),
                        max(0, m.y0 - padding),
                        min(page.rect.width, m.x1 + padding),
                        min(page.rect.height, m.y1 + padding)
                    )
                    if m_padded.width <= 0 or m_padded.height <= 0:
                        continue
                    nome_temp = gerar_nome(output_dir, prefixo, page_index, "drawing", el["idx"], "png")
                    matrix = fitz.Matrix(2, 2)
                    pix = page.get_pixmap(clip=m_padded, matrix=matrix)
                    if pix.width <= 0 or pix.height <= 0:
                        continue
                    pix.save(nome_temp)
                    nome_webp = converter_para_webp(nome_temp)
                    imagens.append({
                        "pagina": page_index,
                        "y": m_padded.y0,
                        "x": m_padded.x0,
                        "largura": m_padded.width,
                        "arquivo": nome_webp
                    })

    return imagens

