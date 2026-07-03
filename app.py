import os
import tempfile
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import RedirectResponse
from extratorUNICAMP import (
    extrair_prova_objetiva,
    extrair_prova_dissertativa,
    extrair_e_salvar_prova_objetiva,
    extrair_e_salvar_prova_dissertativa,
)
from models import Questao

app = FastAPI(
    title="Extrator de Provas - API REST & SDK Python",
    description=(
        "### 🎯 Bem-vindo ao Extrator de Provas do Vestibular!\n\n"
        "Este projeto foi desenvolvido com uma arquitetura dual: funciona tanto como uma **biblioteca Python (SDK)** "
        "quanto como uma **Web API (REST)** baseada em FastAPI.\n\n"
        "---\n\n"
        "### 📦 1. Uso como Biblioteca Python (SDK)\n"
        "Se você deseja integrar a extração diretamente em seus scripts Python (sem fazer requisições de rede):\n\n"
        "* **Instalação local**: Navegue até a pasta `Projeto_API` e execute:\n"
        "  ```bash\n"
        "  pip install -e .\n"
        "  ```\n"
        "* **Como importar e utilizar no seu código**:\n"
        "  ```python\n"
        "  import extratorUNICAMP\n\n"
        "  # 1. Extração de Prova Objetiva (1ª Fase)\n"
        "  questoes = extratorUNICAMP.objetiva(\"prova.pdf\", \"gabarito.pdf\")\n\n"
        "  # 2. Extração de Prova Dissertativa (2ª Fase)\n"
        "  questoes_dis = extratorUNICAMP.dissertativa(\"prova_2fase.pdf\")\n"
        "  ```\n\n"
        "---\n\n"
        "### ⚡ 2. Uso como Web API (REST)\n"
        "Os endpoints listados abaixo permitem integrar o extrator com outros sistemas através de requisições HTTP POST. "
        "Eles possuem **polimorfismo de entrada**: você pode optar por fazer o **upload do PDF** diretamente na requisição "
        "OU apenas enviar o **caminho do arquivo local** no servidor."
    ),
    version="1.0.0",
)

@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    """Redireciona automaticamente a raiz para a página de documentação interativa (Swagger)."""
    return RedirectResponse(url="/docs")


# ==========================================
# 1. Endpoints de Extração em Memória (Retornam JSON)
# ==========================================

@app.post(
    "/extrair/objetiva",
    response_model=List[Questao],
    summary="Extrair Prova Objetiva (1ª Fase) em Memória",
    description=(
        "Permite extrair as questões enviando o PDF da prova via upload OU fornecendo seu caminho local no servidor. "
        "O gabarito oficial também pode ser enviado via upload ou caminho local."
    ),
)
async def api_extrair_prova_objetiva(
    prova: Optional[UploadFile] = File(None, description="Arquivo PDF da prova objetiva (upload)"),
    caminho_prova: Optional[str] = Form(None, description="Caminho local do PDF da prova no servidor"),
    gabarito: Optional[UploadFile] = File(None, description="Arquivo PDF do gabarito oficial (upload)"),
    caminho_gabarito: Optional[str] = Form(None, description="Caminho local do PDF do gabarito no servidor")
):
    caminho_prova_final = None
    prova_temp_criada = False
    
    # 1. Resolver o caminho da prova
    if caminho_prova and caminho_prova.strip():
        caminho_prova_final = caminho_prova.strip()
        if not os.path.exists(caminho_prova_final):
            raise HTTPException(status_code=400, detail=f"Arquivo de prova não encontrado: {caminho_prova_final}")
    elif prova:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_prova:
            content = await prova.read()
            tmp_prova.write(content)
            caminho_prova_final = tmp_prova.name
            prova_temp_criada = True
    else:
        raise HTTPException(
            status_code=400, 
            detail="Forneça a prova por upload (campo 'prova') OU por caminho local (campo 'caminho_prova')."
        )
        
    # 2. Resolver o caminho do gabarito
    caminho_gabarito_final = None
    gabarito_temp_criada = False
    
    if caminho_gabarito and caminho_gabarito.strip():
        caminho_gabarito_final = caminho_gabarito.strip()
        if not os.path.exists(caminho_gabarito_final):
            if prova_temp_criada and os.path.exists(caminho_prova_final):
                os.unlink(caminho_prova_final)
            raise HTTPException(status_code=400, detail=f"Arquivo de gabarito não encontrado: {caminho_gabarito_final}")
    elif gabarito:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_gabarito:
            content_g = await gabarito.read()
            tmp_gabarito.write(content_g)
            caminho_gabarito_final = tmp_gabarito.name
            gabarito_temp_criada = True
            
    # 3. Executar a extração
    try:
        questoes = extrair_prova_objetiva(caminho_prova_final, caminho_gabarito_final)
        return questoes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na extração: {str(e)}")
    finally:
        # Limpeza de arquivos temporários
        if prova_temp_criada and caminho_prova_final and os.path.exists(caminho_prova_final):
            try: os.unlink(caminho_prova_final)
            except Exception: pass
        if gabarito_temp_criada and caminho_gabarito_final and os.path.exists(caminho_gabarito_final):
            try: os.unlink(caminho_gabarito_final)
            except Exception: pass

@app.post(
    "/extrair/dissertativa",
    response_model=List[Questao],
    summary="Extrair Prova Dissertativa (2ª Fase) em Memória",
    description=(
        "Permite extrair as questões enviando o PDF da prova dissertativa via upload OU fornecendo seu caminho local no servidor."
    ),
)
async def api_extrair_prova_dissertativa(
    prova: Optional[UploadFile] = File(None, description="Arquivo PDF da prova dissertativa (upload)"),
    caminho_prova: Optional[str] = Form(None, description="Caminho local do PDF da prova dissertativa no servidor")
):
    caminho_prova_final = None
    prova_temp_criada = False
    
    # 1. Resolver o caminho da prova
    if caminho_prova and caminho_prova.strip():
        caminho_prova_final = caminho_prova.strip()
        if not os.path.exists(caminho_prova_final):
            raise HTTPException(status_code=400, detail=f"Arquivo de prova não encontrado: {caminho_prova_final}")
    elif prova:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_prova:
            content = await prova.read()
            tmp_prova.write(content)
            caminho_prova_final = tmp_prova.name
            prova_temp_criada = True
    else:
        raise HTTPException(
            status_code=400, 
            detail="Forneça a prova por upload (campo 'prova') OU por caminho local (campo 'caminho_prova')."
        )
        
    # 2. Executar a extração
    try:
        questoes = extrair_prova_dissertativa(caminho_prova_final)
        return questoes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na extração: {str(e)}")
    finally:
        if prova_temp_criada and caminho_prova_final and os.path.exists(caminho_prova_final):
            try: os.unlink(caminho_prova_final)
            except Exception: pass


# ==========================================
# 2. Endpoints de Extração e Gravação Direta em Disco no Servidor
# ==========================================

@app.post(
    "/extrair-e-salvar/objetiva",
    summary="Extrair e Salvar Prova Objetiva (1ª Fase) em Disco",
    description=(
        "Realiza a extração e grava os JSONs e imagens na pasta destino especificada no servidor. "
        "A prova e o gabarito podem ser fornecidos por upload OU por caminhos de arquivos locais."
    ),
)
async def api_extrair_e_salvar_prova_objetiva(
    pasta_destino: str = Form(..., description="Caminho do diretório no servidor onde os JSONs e imagens serão salvos"),
    prova: Optional[UploadFile] = File(None, description="Arquivo PDF da prova objetiva (upload)"),
    caminho_prova: Optional[str] = Form(None, description="Caminho local do PDF da prova no servidor"),
    gabarito: Optional[UploadFile] = File(None, description="Arquivo PDF do gabarito oficial (upload)"),
    caminho_gabarito: Optional[str] = Form(None, description="Caminho local do PDF do gabarito no servidor")
):
    caminho_prova_final = None
    prova_temp_criada = False
    
    # 1. Resolver o caminho da prova
    if caminho_prova and caminho_prova.strip():
        caminho_prova_final = caminho_prova.strip()
        if not os.path.exists(caminho_prova_final):
            raise HTTPException(status_code=400, detail=f"Arquivo de prova não encontrado: {caminho_prova_final}")
    elif prova:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_prova:
            content = await prova.read()
            tmp_prova.write(content)
            caminho_prova_final = tmp_prova.name
            prova_temp_criada = True
    else:
        raise HTTPException(
            status_code=400, 
            detail="Forneça a prova por upload (campo 'prova') OU por caminho local (campo 'caminho_prova')."
        )
        
    # 2. Resolver o caminho do gabarito
    caminho_gabarito_final = None
    gabarito_temp_criada = False
    
    if caminho_gabarito and caminho_gabarito.strip():
        caminho_gabarito_final = caminho_gabarito.strip()
        if not os.path.exists(caminho_gabarito_final):
            if prova_temp_criada and os.path.exists(caminho_prova_final):
                os.unlink(caminho_prova_final)
            raise HTTPException(status_code=400, detail=f"Arquivo de gabarito não encontrado: {caminho_gabarito_final}")
    elif gabarito:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_gabarito:
            content_g = await gabarito.read()
            tmp_gabarito.write(content_g)
            caminho_gabarito_final = tmp_gabarito.name
            gabarito_temp_criada = True
            
    # 3. Executar a gravação
    try:
        extrair_e_salvar_prova_objetiva(caminho_prova_final, pasta_destino, caminho_gabarito_final)
        return {
            "status": "sucesso",
            "mensagem": f"Prova objetiva extraída e gravada com sucesso na pasta '{pasta_destino}'."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na extração/gravação: {str(e)}")
    finally:
        if prova_temp_criada and caminho_prova_final and os.path.exists(caminho_prova_final):
            try: os.unlink(caminho_prova_final)
            except Exception: pass
        if gabarito_temp_criada and caminho_gabarito_final and os.path.exists(caminho_gabarito_final):
            try: os.unlink(caminho_gabarito_final)
            except Exception: pass

@app.post(
    "/extrair-e-salvar/dissertativa",
    summary="Extrair e Salvar Prova Dissertativa (2ª Fase) em Disco",
    description=(
        "Realiza a extração e grava os JSONs e imagens na pasta destino especificada no servidor. "
        "A prova pode ser fornecida por upload OU por caminho de arquivo local."
    ),
)
async def api_extrair_e_salvar_prova_dissertativa(
    pasta_destino: str = Form(..., description="Caminho do diretório no servidor onde os JSONs e imagens serão salvos"),
    prova: Optional[UploadFile] = File(None, description="Arquivo PDF da prova dissertativa (upload)"),
    caminho_prova: Optional[str] = Form(None, description="Caminho local do PDF da prova dissertativa no servidor")
):
    caminho_prova_final = None
    prova_temp_criada = False
    
    # 1. Resolver o caminho da prova
    if caminho_prova and caminho_prova.strip():
        caminho_prova_final = caminho_prova.strip()
        if not os.path.exists(caminho_prova_final):
            raise HTTPException(status_code=400, detail=f"Arquivo de prova não encontrado: {caminho_prova_final}")
    elif prova:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_prova:
            content = await prova.read()
            tmp_prova.write(content)
            caminho_prova_final = tmp_prova.name
            prova_temp_criada = True
    else:
        raise HTTPException(
            status_code=400, 
            detail="Forneça a prova por upload (campo 'prova') OU por caminho local (campo 'caminho_prova')."
        )
        
    # 2. Executar a gravação
    try:
        extrair_e_salvar_prova_dissertativa(caminho_prova_final, pasta_destino)
        return {
            "status": "sucesso",
            "mensagem": f"Prova dissertativa extraída e gravada com sucesso na pasta '{pasta_destino}'."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na extração/gravação: {str(e)}")
    finally:
        if prova_temp_criada and caminho_prova_final and os.path.exists(caminho_prova_final):
            try: os.unlink(caminho_prova_final)
            except Exception: pass


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    mapeamento = {
        "Body_api_extrair_prova_objetiva_extrair_objetiva_post": "ExtrairObjetivaRequest",
        "Body_api_extrair_prova_dissertativa_extrair_dissertativa_post": "ExtrairDissertativaRequest",
        "Body_api_extrair_e_salvar_prova_objetiva_extrair_e_salvar_objetiva_post": "SalvarObjetivaRequest",
        "Body_api_extrair_e_salvar_prova_dissertativa_extrair_e_salvar_dissertativa_post": "SalvarDissertativaRequest"
    }
    
    # 1. Renomear nos components/schemas e atualizar title
    schemas = openapi_schema.get("components", {}).get("schemas", {})
    for nome_antigo, nome_novo in mapeamento.items():
        if nome_antigo in schemas:
            schemas[nome_novo] = schemas.pop(nome_antigo)
            if isinstance(schemas[nome_novo], dict) and "title" in schemas[nome_novo]:
                schemas[nome_novo]["title"] = nome_novo
            
    # 2. Atualizar todas as referências ($ref) recursivamente no schema JSON
    def atualizar_refs(obj):
        if isinstance(obj, dict):
            for k, v in list(obj.items()):
                if k == "$ref" and isinstance(v, str):
                    for nome_antigo, nome_novo in mapeamento.items():
                        if v.endswith(f"/schemas/{nome_antigo}"):
                            obj[k] = v.replace(f"/schemas/{nome_antigo}", f"/schemas/{nome_novo}")
                else:
                    atualizar_refs(v)
        elif isinstance(obj, list):
            for item in obj:
                atualizar_refs(item)
                
    atualizar_refs(openapi_schema)
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    # Executa o servidor na porta 8000
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
