import re
import os
import time
from typing import Optional, List
import fitz
from models import *
from extractor import encontrar_labels_alternativas, map_image, linhas_por_coluna, IMG_REL_PREFIX

try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# Constantes globais do módulo
TAMANHO_LOTE_IA = 20
INTERVALO_MIN_RPM = 4.5

TAG_BLACKLIST = {
    "unicamp", "fuvest", "enem", "vestibular", "prova", "questão", "questao", "questoes", "questões",
    "matemática", "matematica", "física", "fisica", "química", "quimica", "biologia", "história", "historia",
    "geografia", "português", "portugues", "literatura", "inglês", "ingles", "filosofia", "sociologia", 
    "espanhol", "humanas", "exatas", "ciências", "ciencias", "ciências da natureza", "ciências humanas",
    "geral", "materia", "disciplina", "desconhecida", "desconhecido"
}

def formatar_tempo(segundos):
    minutos = int(segundos // 60)
    segs = int(segundos % 60)
    if minutos > 0:
        return f"{minutos} min {segs} s"
    return f"{segs} s"

def chave_valida(key: str) -> bool:
    return bool(key and key.strip() and key.strip() != "INSIRA_SUA_CHAVE_GEMINI_AQUI")

def obter_subtopicos_por_materia(materia: str) -> Optional[List[str]]:
    """
    Stub: retorna subtópicos conhecidos para a matéria informada.
    Implementar futuramente com o mapeamento completo matéria -> subtópicos.
    """
    return None

def extrair_textos_comp(texto):
    padrao = r"(Texto para as questões ([\d,\se]+)\.\n)(.*?)(?=QUESTÃO|\Z)"
    resultados = []
    for match in re.finditer(padrao, texto, re.DOTALL):
        numeros = re.findall(r"\d+", match.group(2))
        conteudo = match.group(3).strip()
        resultados.append(
            TextoComplementar(
                metadadosComp=MetadadosComp(codigos_questoes=numeros),
                conteudoComp=ConteudoComp(enunciado=conteudo)
            )
        )
    return resultados

def detectar_edital_ano(pdf_path):
    """
    Detecta dinamicamente o edital, o ano e a cor/tipo da prova a partir do nome do arquivo ou do caminho.
    """
    nome_arquivo = os.path.basename(pdf_path).lower()

    edital = "unicamp"
    if "enem" in nome_arquivo:
        edital = "enem"
    elif "fuvest" in nome_arquivo:
        edital = "fuvest"
    elif "unicamp" in nome_arquivo:
        edital = "unicamp"

    ano = 2026
    match_ano = re.search(r"\b(200[6-9]|20[1-9]\d)\b", nome_arquivo)
    if not match_ano:
        match_ano = re.search(r"\b(200[6-9]|20[1-9]\d)\b", pdf_path)
    if match_ano:
        ano = int(match_ano.group(1))

    tipo_prova = "Q-X"
    # Palavras-chave específicas para a 2ª fase (checando no caminho completo e no nome do arquivo)
    caminho_completo_lc = pdf_path.lower()
    if "biologia" in caminho_completo_lc or "biologica" in caminho_completo_lc or "saude" in caminho_completo_lc:
        tipo_prova = "BIOLOGICAS"
    elif "exata" in caminho_completo_lc or "tecnolo" in caminho_completo_lc:
        tipo_prova = "EXATAS"
    elif "humana" in caminho_completo_lc or "artes" in caminho_completo_lc:
        tipo_prova = "HUMANAS"
    elif "redacao" in caminho_completo_lc or "portugues" in caminho_completo_lc or "literatura" in caminho_completo_lc or "ingles" in caminho_completo_lc:
        tipo_prova = "REDACAO"
    elif "dia-1" in caminho_completo_lc or "dia1" in caminho_completo_lc:
        tipo_prova = "DIA1"
    elif "dia-2" in caminho_completo_lc or "dia2" in caminho_completo_lc:
        tipo_prova = "DIA2"
    else:
        for cor in ["azul", "amarelo", "rosa", "verde", "cinza", "branco", "preto", "laranja"]:
            if cor in nome_arquivo:
                tipo_prova = cor.upper()
                break
        else:
            # Formato "X-e-Y" (ex: "provas-unicamp-2023-q-e-z.pdf")
            match_triple = re.search(r"\b([a-z])\s*[-]\s*e\s*[-]\s*([a-z])\b", nome_arquivo)
            if match_triple:
                tipo_prova = f"{match_triple.group(1)}-{match_triple.group(2)}".upper()
            else:
                # Formato "X-Y" (ex: "prova-q-x.pdf")
                match_letras = re.search(r"\b([a-z])\s*[-]\s*([a-z])\b", nome_arquivo)
                if match_letras:
                    tipo_prova = f"{match_letras.group(1)}-{match_letras.group(2)}".upper()
                else:
                    # Formato "X e Y" (ex: "Provas E e G.pdf")
                    match_letras_e = re.search(r"\b([a-z])\s+e\s+([a-z])\b", nome_arquivo)
                    if match_letras_e:
                        tipo_prova = f"{match_letras_e.group(1)}-{match_letras_e.group(2)}".upper()
                    else:
                        # Formato geral "prova-X"
                        match_gen = re.search(r"(?:prova|caderno)-([a-z0-9]+)", nome_arquivo)
                        if match_gen:
                            tipo_prova = match_gen.group(1).upper()

    return edital, ano, tipo_prova

def extrair_questoes(texto, edital="unicamp", ano=2026, tipo_prova="Q-X"):
    padrao = r"(QUESTÃO\s+(\d+))(.*?)(?=QUESTÃO\s+\d+|\Z)"
    questoes = []

    for match in re.finditer(padrao, texto, re.DOTALL):
        numero = int(match.group(2))
        bloco = match.group(3).strip()
        # Pré-processamento: insere quebra de linha antes de alternativas dispostas horizontalmente
        bloco = re.sub(r'[ \t]+\b([b-e])\)\s+', r'\n\1) ', bloco)
        partes = re.split(r"\n\s*([a-e])\)\s*", bloco)
        enunciado = partes[0].strip()

        alt_dict = {partes[i].lower(): AlternativaItem(texto=partes[i+1].strip()) for i in range(1, len(partes) - 1, 2)}

        # Fallback se não conseguir extrair pelo menos as 4 alternativas padrão (a-d)
        if len(alt_dict) < 4:
            partes_fallback = re.split(r"^([a-e])\)\s*", bloco, flags=re.MULTILINE)
            if len(partes_fallback) > len(partes):
                partes = partes_fallback
                enunciado = partes[0].strip()
                alt_dict = {partes[i].lower(): AlternativaItem(texto=partes[i+1].strip()) for i in range(1, len(partes) - 1, 2)}

        questoes.append(
            Questao(
                metadados=Metadados(
                    codigo=f"{edital}_{ano}_q{numero}",
                    edital=edital,
                    numero=numero,
                    tipo_ou_cor=tipo_prova,
                    ano=ano
                ),
                conteudo=Conteudo(enunciado=enunciado, objetiva=True),
                especificacao=Especificacao(disciplina=[], assunto=[], topicos=[]),
                alternativas=Alternativas(
                    a=alt_dict.get("a", AlternativaItem()),
                    b=alt_dict.get("b", AlternativaItem()),
                    c=alt_dict.get("c", AlternativaItem()),
                    d=alt_dict.get("d", AlternativaItem()),
                    e=alt_dict.get("e")
                )
            )
        )

    return questoes

def extrair_questoes_dissertativas(texto, edital="unicamp", ano=2026, tipo_prova="Q-X"):
    questoes = []
    
    # Padrão flexível para cobrir variações de caneta ("preta" ou comum) e "RASCUNHO" no cabeçalho
    padrao_header = r"Resolu[çc]\u00e3o\s+\(ser\u00e1\s+considerado\s+apenas\s+o\s+que\s+estiver\s+(?:escrito\s+com\s+caneta\s+(?:preta\s+)?)?dentro\s+deste\s+espa[çc]o\)\s*\.?\s*(?:RASCUNHO)?"
    partes = re.split(padrao_header, texto, flags=re.IGNORECASE)
    
    num_questoes = len(partes) - 1
    if num_questoes <= 0:
        # Fallback caso não encontre divisões: processa o texto inteiro como única questão ou ignora
        num_questoes = 1
        partes = [texto, ""]
    
    for i in range(num_questoes):
        bloco_bruto = partes[i]
        numero = i + 1
        
        # Buscamos o início da questão correspondente na parte correspondente
        if numero == 1:
            match = re.search(r"(?:^|\n)\s*1\.\s+(.*)", bloco_bruto, re.DOTALL)
        else:
            match = re.search(rf"(?:^|\n)\s*{numero}\.\s+(.*)", bloco_bruto, re.DOTALL)
            
        if match:
            bloco = match.group(1).strip()
            
            # Limpa marcas indesejadas
            bloco = re.sub(r"\bRASCUNHO\b", "", bloco, flags=re.IGNORECASE)
            bloco = re.sub(r"\bD\d+\b", "", bloco)
            
            questoes.append(
                Questao(
                    metadados=Metadados(
                        codigo=f"{edital}_{ano}_q{numero}",
                        edital=edital,
                        numero=numero,
                        tipo_ou_cor=tipo_prova,
                        ano=ano
                    ),
                    conteudo=Conteudo(enunciado=bloco.strip(), objetiva=False),
                    especificacao=Especificacao(disciplina=[], assunto=[], topicos=[])
                )
            )
    return questoes


def mapear_textos_comp(textos_comp):
    mapa = {}
    for t in textos_comp:
        for cod in t.metadadosComp.codigos_questoes:
            mapa[int(cod)] = t
    return mapa

def localizar_questoes(paginas):
    posicoes = []
    for p in paginas:
        page = p["page"]
        mid_x = page.rect.width / 2
        d = page.get_text("dict")
        for b in d["blocks"]:
            if b["type"] == 0:  # Texto
                for line in b["lines"]:
                    line_text = "".join(span["text"] for span in line["spans"])
                    match = re.search(r"QUESTÃO\s+(\d+)|^\s*(\d+)\.\s+[A-Za-zÀ-ÿ]", line_text)
                    if match:
                        num = int(match.group(1) or match.group(2))
                        x0, y0, x1, y1 = line["bbox"]
                        centro_x = (x0 + x1) / 2
                        col = "esquerda" if centro_x < mid_x else "direita"
                        posicoes.append({
                            "numero": num,
                            "pagina": p["numero"],
                            "y": y0,
                            "coluna": col
                        })
    posicoes.sort(key=lambda x: (x["pagina"], x["y"]))
    return posicoes

def associar_imagens(questoes_pos, imagens):
    mapa = {q["numero"]: [] for q in questoes_pos}
    for img in imagens:
        img_pos = (img["pagina"], img["y"])
        melhor_q = None
        for q in questoes_pos:
            q_pos = (q["pagina"], q["y"])
            if q_pos <= img_pos:
                melhor_q = q["numero"]
            else:
                break
        if melhor_q:
            mapa[melhor_q].append(img["arquivo"])
    return mapa

def enriquecer(questoes, mapa_textos, mapa_imgs):
    for q in questoes:
        q.conteudo.url_img = re.findall(r"!\[.*?\]\((.*?)\)", q.conteudo.enunciado)
        if q.alternativas is not None:
            for letra in ["a", "b", "c", "d", "e"]:
                alt = getattr(q.alternativas, letra)
                if alt and alt.texto:
                    alt.url_img = re.findall(r"!\[.*?\]\((.*?)\)", alt.texto)
        if getattr(q, "sub_itens", None) is not None:
            for sub in q.sub_itens:
                if sub.texto:
                    sub.url_img = re.findall(r"!\[.*?\]\((.*?)\)", sub.texto)
    return questoes

def mapear_imagens_a_questoes_e_alternativas(questoes, imagens, doc):
    """
    Mapeia cada imagem da prova para a sua respectiva questão e alternativa (ou enunciado)
    usando a ordem de leitura global (coluna esquerda primeiro, depois direita por página)
    para associar de forma robusta e precisa.
    """
    mapa_questoes = {q.metadados.numero: q for q in questoes}
    
    # 1. Agrupar imagens por página
    imgs_por_pagina = {}
    for img in imagens:
        p = img["pagina"]
        if p not in imgs_por_pagina:
            imgs_por_pagina[p] = []
        imgs_por_pagina[p].append(img)
        
    global_elements = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        mid_x = page.rect.width / 2
        
        elementos_esquerda = []
        elementos_direita = []
        
        # Obter linhas de texto
        left_lines, right_lines = linhas_por_coluna(page, mid_x)
        for line in left_lines:
            elementos_esquerda.append({
                "tipo": "texto",
                "y": line["y"],
                "texto": line["texto"],
                "pagina": page_num
            })
        for line in right_lines:
            elementos_direita.append({
                "tipo": "texto",
                "y": line["y"],
                "texto": line["texto"],
                "pagina": page_num
            })
                        
        # Obter imagens desta página
        page_imgs = imgs_por_pagina.get(page_num, [])
        for img in page_imgs:
            img_x = img.get("x", 0)
            img_y = img["y"]
            centro_x = img_x + img.get("largura", 0) / 2
            coluna_img = "esquerda" if centro_x < mid_x else "direita"
            el_img = {
                "tipo": "imagem",
                "y": img_y,
                "x": img_x,
                "largura": img.get("largura", 0),
                "arquivo": img["arquivo"],
                "pagina": page_num
            }
            if coluna_img == "esquerda":
                elementos_esquerda.append(el_img)
            else:
                elementos_direita.append(el_img)
                
        elementos_esquerda.sort(key=lambda x: x["y"])
        elementos_direita.sort(key=lambda x: x["y"])
        
        global_elements.extend(elementos_esquerda + elementos_direita)
        
    # 2. Rastrear a questão ativa e associar as imagens
    questao_atual = None
    for idx_el, el in enumerate(global_elements):
        if el["tipo"] == "texto":
            match = re.search(r"QUESTÃO\s+(\d+)|^\s*(\d+)\.\s+[A-Za-zÀ-ÿ]", el["texto"])
            if match:
                questao_atual = int(match.group(1) or match.group(2))
        elif el["tipo"] == "imagem":
            q_alvo = questao_atual
            forcar_enunciado = False
            if questao_atual is not None:
                for next_el in global_elements[idx_el+1:]:
                    if next_el["tipo"] == "texto":
                        if next_el["pagina"] != el["pagina"]:
                            break
                        match_next = re.search(r"QUESTÃO\s+(\d+)|^\s*(\d+)\.\s+[A-Za-zÀ-ÿ]", next_el["texto"])
                        if match_next:
                            dist_y = next_el["y"] - el["y"]
                            if 0 < dist_y <= 50:
                                q_alvo = int(match_next.group(1) or match_next.group(2))
                                forcar_enunciado = True
                            break
                        if next_el["y"] - el["y"] > 50:
                            break
            if q_alvo is not None and q_alvo in mapa_questoes:
                q_obj = mapa_questoes[q_alvo]
                page_idx = el["pagina"]
                page = doc[page_idx]
                mid_x = page.rect.width / 2
                if forcar_enunciado or getattr(q_obj, 'alternativas', None) is None:
                    letra_mapped = "enunciado"
                else:
                    labels_pagina = encontrar_labels_alternativas(page, mid_x)
                    letra_mapped = map_image(el["y"], el["x"], mid_x, labels_pagina, img_w=el.get("largura", 0), page=page)
                
                img_caminho = f"{IMG_REL_PREFIX}{os.path.basename(el['arquivo'])}"
                
                if letra_mapped == "enunciado" or letra_mapped is None:
                    if img_caminho not in q_obj.conteudo.url_img:
                        q_obj.conteudo.url_img.append(img_caminho)
                    tag = f'\n\n![figura]({img_caminho})\n\n'
                    if tag not in q_obj.conteudo.enunciado:
                        q_obj.conteudo.enunciado += tag
                else:
                    alt = getattr(q_obj.alternativas, letra_mapped)
                    if alt:
                        if img_caminho not in alt.url_img:
                            alt.url_img.append(img_caminho)
                        tag = f'\n\n![figura]({img_caminho})\n\n'
                        if not alt.texto:
                            alt.texto = tag.strip()
                        elif tag not in alt.texto:
                            alt.texto += tag

    # 3. Renomear fisicamente as imagens e atualizar as referências nos objetos Questao
    caminho_absoluto = {os.path.basename(img['arquivo']): img for img in imagens}
    renomeados = {}
    
    for q_obj in questoes:
        edital = q_obj.metadados.edital
        ano = q_obj.metadados.ano
        tipo = q_obj.metadados.tipo_ou_cor.replace('/', '-')
        num = q_obj.metadados.numero
        
        # Coletar todas as imagens da questão na ordem em que aparecem
        imagens_da_questao = []
        for img in q_obj.conteudo.url_img:
            if img not in imagens_da_questao:
                imagens_da_questao.append(img)
        if q_obj.alternativas:
            for letra in ["a", "b", "c", "d", "e"]:
                alt = getattr(q_obj.alternativas, letra)
                if alt and alt.url_img:
                    for img in alt.url_img:
                        if img not in imagens_da_questao:
                            imagens_da_questao.append(img)
                            
        # Renomear cada imagem e atualizar referências
        for idx, img_rel_old in enumerate(imagens_da_questao):
            basename_old = os.path.basename(img_rel_old)
            
            if basename_old in renomeados:
                img_rel_new = renomeados[basename_old]
            else:
                img_dict = caminho_absoluto.get(basename_old)
                if img_dict:
                    abs_old = img_dict["arquivo"]
                    if os.path.exists(abs_old):
                        if "group" in basename_old:
                            img_dict["grupo"] = True
                        
                        ext = os.path.splitext(basename_old)[1] or ".webp"
                        # Exemplo: unicamp_2019_Q-Y_q6_img_1.webp
                        basename_new = f"{edital}_{ano}_{tipo}_q{num}_img_{idx + 1}{ext}"
                        abs_new = os.path.join(os.path.dirname(abs_old), basename_new)
                        
                        try:
                            if os.path.exists(abs_new):
                                os.remove(abs_new)
                            os.rename(abs_old, abs_new)
                            img_rel_new = f"{IMG_REL_PREFIX}{basename_new}"
                            renomeados[basename_old] = img_rel_new
                            img_dict["arquivo"] = abs_new
                        except Exception as e:
                            print(f"[Aviso] Falha ao renomear {abs_old} para {abs_new}: {e}")
                            img_rel_new = img_rel_old
                    else:
                        img_rel_new = img_rel_old
                else:
                    img_rel_new = img_rel_old
            
            # Atualizar referências no objeto Questao
            if img_rel_old != img_rel_new:
                # 1. No enunciado
                if img_rel_old in q_obj.conteudo.url_img:
                    q_obj.conteudo.url_img = [img_rel_new if x == img_rel_old else x for x in q_obj.conteudo.url_img]
                q_obj.conteudo.enunciado = q_obj.conteudo.enunciado.replace(img_rel_old, img_rel_new)
                
                # 2. Nas alternativas
                if q_obj.alternativas:
                    for letra in ["a", "b", "c", "d", "e"]:
                        alt = getattr(q_obj.alternativas, letra)
                        if alt:
                            if alt.url_img and img_rel_old in alt.url_img:
                                alt.url_img = [img_rel_new if x == img_rel_old else x for x in alt.url_img]
                            if alt.texto:
                                alt.texto = alt.texto.replace(img_rel_old, img_rel_new)

def extrair_gabarito(gabarito_path):
    doc = fitz.open(gabarito_path)
    resultados_paginas = []

    for page in doc:
        texto_pagina = page.get_text()
        
        # Encontra respostas na página atual
        pares = re.findall(r"(\d{1,2})\s*\n\s*([A-E*a-e])\s*(?=\n|\Z)", texto_pagina)
        respostas = {}
        for num_str, letra in pares:
            respostas[int(num_str)] = letra.lower()
            
        # Detecta tipo do gabarito na página atual
        tipo_match = re.search(r"PROVAS\s+([A-Za-z\s\-e]+)", texto_pagina, re.IGNORECASE)
        if tipo_match:
            tipo_gabarito = tipo_match.group(1).split("\n")[0].strip()
        else:
            tipo_gabarito = "Desconhecido"
        
        if respostas:
            resultados_paginas.append((respostas, tipo_gabarito))

    # Verifica se existem tipos diferentes no documento
    tipos_unicos = set(t for _, t in resultados_paginas if t != "Desconhecido")
    
    if len(tipos_unicos) > 1:
        return resultados_paginas
    elif len(resultados_paginas) == 1:
        return resultados_paginas[0][0], resultados_paginas[0][1]
    elif len(resultados_paginas) > 1:
        todas_respostas = {}
        tipo_final = "Desconhecido"
        for resp, t in resultados_paginas:
            todas_respostas.update(resp)
            if t != "Desconhecido":
                tipo_final = t
        return todas_respostas, tipo_final
    else:
        return {}, "Desconhecido"

def aplicar_gabarito(questoes, respostas):
    for q in questoes:
        num = q.metadados.numero
        if num in respostas:
            resp_correta = respostas[num]
            for letra in ["a", "b", "c", "d", "e"]:
                alt = getattr(q.alternativas, letra)
                if alt:
                    alt.correta = (resp_correta == letra)
    return questoes

def carregar_env(caminho_env=".env"):
    """
    Leitor nativo e seguro para arquivos .env (sem dependências externas)
    """
    if not os.path.exists(caminho_env):
        pasta_script = os.path.dirname(os.path.abspath(__file__))
        caminho_env = os.path.join(pasta_script, ".env")
    if os.path.exists(caminho_env):
        with open(caminho_env, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    chave, valor = line.split("=", 1)
                    val = valor.strip().strip('"').strip("'")
                    os.environ[chave.strip()] = val

def enriquecer_questoes_com_ia(questoes, api_key, mapa_textos=None, max_questoes=None):
    """
    Enriquece as questões da prova com resoluções, dicas, matéria e tags geradas por IA.
    Processa as questões em lotes de 20 para otimizar custos e velocidade.
    A estimativa de tempo restante é dinâmica, baseada no tempo real medido da primeira chamada.
    Aplica filtro programático complementar (blacklist) nas tags retornadas.
    """
    if not HAS_GEMINI:
        print("\n[IA Gemini] A biblioteca 'google-genai' não está instalada.")
        print("Para ativar enriquecimento automático por IA, instale rodando:")
        print("  pip install google-genai")
        return questoes

    if not chave_valida(api_key):
        print("\n[IA Gemini] Chave de API do Gemini não configurada no arquivo '.env'.")
        print("Insira sua chave no arquivo '.env' local para habilitar o preenchimento automático por IA.")
        return questoes

    questoes_para_processar = questoes[:max_questoes] if max_questoes is not None else questoes
    total = len(questoes_para_processar)
    if total == 0:
        return questoes

    lotes = [questoes_para_processar[x:x+TAMANHO_LOTE_IA] for x in range(0, total, TAMANHO_LOTE_IA)]
    total_lotes = len(lotes)

    print(f"\nIniciando enriquecimento de {total} questões em {total_lotes} lotes (limite de 20 por lote) via IA (Google Gemini)...")
    print(f"Aviso: Chamadas espaçadas dinamicamente (garantindo intervalo mínimo de {INTERVALO_MIN_RPM}s desde o início do lote anterior) para respeitar o limite de 15 RPM da API.")

    tempo_primeira_req = None
    tempo_ultimo_inicio = None

    try:
        client = genai.Client(api_key=api_key)
        mapa_questoes_obj = {q.metadados.numero: q for q in questoes_para_processar}

        for idx, lote in enumerate(lotes):
            if idx > 0 and tempo_ultimo_inicio is not None:
                tempo_decorrido = time.time() - tempo_ultimo_inicio
                espera_necessaria = INTERVALO_MIN_RPM - tempo_decorrido
                if espera_necessaria > 0:
                    time.sleep(espera_necessaria)

            tempo_ultimo_inicio = time.time()
            print(f"\n[IA Gemini] Processando lote {idx+1} de {total_lotes} (Questões: {', '.join(str(q.metadados.numero) for q in lote)})...")

            prompt = """Você é um professor especialista em vestibulares (como UNICAMP, FUVEST, ENEM).
Analise as seguintes questões do vestibular e forneça de maneira estruturada:
1. Disciplinas relacionadas como lista de strings (ex: ["História"], ["Física", "Matemática"]).
2. Assuntos/temas de estudo abordados na questão como lista de strings (ex: ["Segunda Guerra Mundial"], ["Termodinâmica"]).
3. Tópicos específicos de estudo como lista de strings (ex: ["Nazismo", "Holocausto"], ["Leis da Termodinâmica"]).
4. Resolução detalhada passo a passo em português.
5. Dicas de estudo: retorne como lista de strings, com 1 a 3 dicas específicas e distintas relacionadas ao assunto.

Abaixo estão listadas as questões a analisar:
"""
            for q in lote:
                prompt += f"\n--- QUESTÃO {q.metadados.numero} ---\n"
                if mapa_textos and q.metadados.numero in mapa_textos:
                    texto_comp = mapa_textos[q.metadados.numero].conteudoComp.enunciado
                    prompt += f"[TEXTO COMPLEMENTAR DE APOIO]:\n{texto_comp}\n\n"
                
                materia_principal = q.especificacao.disciplina[0] if q.especificacao.disciplina else "desconhecida"
                subtopicos = obter_subtopicos_por_materia(materia_principal)
                if subtopicos is not None:
                    prompt += f"\n[SUBTÓPICOS CONHECIDOS PARA {materia_principal}]: {', '.join(subtopicos)}\n"
                    prompt += "Ao escolher as tags, prefira termos desta lista quando aplicável.\n"

                prompt += f"ENUNCIADO:\n{q.conteudo.enunciado}\n"
                prompt += "ALTERNATIVAS:\n"
                for letra in ["a", "b", "c", "d", "e"]:
                    if q.alternativas:
                        alt = getattr(q.alternativas, letra)
                        if alt:
                            prompt += f"{letra.upper()}) {alt.texto or ''}\n"

            try:
                t_start = time.time()
                resposta = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=LoteAnaliseQuestaoIA
                    )
                )
                t_end = time.time()
                duracao_chamada = t_end - t_start

                if idx == 0:
                    tempo_primeira_req = duracao_chamada
                    print(f"[IA Gemini] Primeira requisição durou {duracao_chamada:.1f} s.")

                dados_lote = LoteAnaliseQuestaoIA.model_validate_json(resposta.text)

                for analise in dados_lote.questoes:
                    num = analise.numero
                    if num in mapa_questoes_obj:
                        q_obj = mapa_questoes_obj[num]
                        
                        # Filtro programático complementar (double-defense) aplicado a listas
                        q_obj.especificacao.disciplina = [
                            d.strip() for d in analise.disciplina
                            if d.strip().lower() not in TAG_BLACKLIST and 
                            len(d.strip()) > 1 and 
                            not any(b in d.strip().lower() for b in ["unicamp", "fuvest", "enem", "vestibular"])
                        ]
                        
                        q_obj.especificacao.assunto = [
                            a.strip() for a in analise.assunto
                            if a.strip().lower() not in TAG_BLACKLIST and 
                            len(a.strip()) > 1 and 
                            not any(b in a.strip().lower() for b in ["unicamp", "fuvest", "enem", "vestibular"])
                        ]
                        
                        q_obj.especificacao.topicos = [
                            t.strip() for t in analise.topicos
                            if t.strip().lower() not in TAG_BLACKLIST and 
                            len(t.strip()) > 1 and 
                            not any(b in t.strip().lower() for b in ["unicamp", "fuvest", "enem", "vestibular"])
                        ]
                        
                        q_obj.conteudo.resolucao = analise.resolucao
                        q_obj.conteudo.dica = analise.dica

                lotes_restantes = total_lotes - (idx + 1)
                tempo_medido = tempo_primeira_req if tempo_primeira_req is not None else 8.0
                tempo_por_lote = max(tempo_medido, INTERVALO_MIN_RPM)
                tempo_restante = lotes_restantes * tempo_por_lote
                tempo_restante_str = formatar_tempo(tempo_restante)
                print(f"Lote {idx+1} de {total_lotes} enriquecido com sucesso. Tempo restante estimado: {tempo_restante_str}")

            except Exception as inner_e:
                print(f"Erro ao processar lote {idx+1} com IA: {inner_e}")

    except Exception as e:
        print(f"Falha crítica na conexão ou inicialização da API do Gemini: {e}")

    return questoes

