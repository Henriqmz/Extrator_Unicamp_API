# Projeto API - Extrator de Provas do Vestibular UNICAMP

Este módulo fornece uma API programática em Python e Web API (FastAPI) para extrair de forma estruturada as questões do vestibular UNICAMP (**edições de 2006 até 2026**), cobrindo tanto a **1ª Fase (Objetiva e Discursiva)** quanto a **2ª Fase (Dissertativa)**.

---

## 📦 Dependências e Instalação

O projeto está configurado como um pacote Python instalável padrão (`setup.py`). As dependências utilizadas incluem:

### 1. Núcleo e Web API (Obrigatórios)
* **`PyMuPDF` (`fitz`):** Leitura geométrica e extração de texto/vetores dos PDFs.
* **`Pillow` (`PIL`):** Processamento e conversão de figuras para WebP.
* **`pydantic`:** Modelagem tipada e validação dos schemas JSON.
* **`fastapi`:** Framework assíncrono para criação dos endpoints REST HTTP.
* **`uvicorn`:** Servidor ASGI para hospedar a API REST.
* **`python-multipart`:** Suporte ao recebimento de arquivos PDF via upload multipart/form-data.
* **`requests`:** Cliente HTTP para os scripts de teste e demonstração (`demo_chamada_api.py`).

### 2. Módulo Opcional de IA & Testes
* **`google-genai` & `python-dotenv`:** Integração com a API do Google Gemini.
* **`pytest`:** Execução da suíte de testes automatizados (`test_api_pytest.py`).

### 💻 Como Instalar

#### Opção A: Como Pacote Editável (Recomendado)
Navegue até a pasta `Projeto_API` no seu terminal e execute:
```bash
pip install -e .
```
*(O `pip` instalará o pacote e baixará automaticamente as dependências de `setup.py`).*

#### Opção B: Instalação Manual de Todas as Bibliotecas
```bash
pip install pymupdf pillow pydantic fastapi uvicorn python-multipart requests google-genai python-dotenv pytest
```

---

## 💻 Como Importar e Utilizar (SDK Python)

```python
import extratorUNICAMP

# 1. Extração em Memória (Retorna lista de objetos Questao)
questoes_obj = extratorUNICAMP.objetiva("prova.pdf", "gabarito.pdf")
questoes_dis = extratorUNICAMP.dissertativa("prova_dis.pdf")

# 2. Extração e Gravação em Disco (Salva JSONs e imagens WebP)
extratorUNICAMP.salvar_objetiva("prova.pdf", "pasta_destino", "gabarito.pdf")
extratorUNICAMP.salvar_dissertativa("prova_dis.pdf", "pasta_destino")
```

---

## ⚡ Execução como Web API (FastAPI)

Navegue até a pasta `Projeto_API` e execute o servidor:
```bash
python app.py
```
O servidor será iniciado em `http://127.0.0.1:8000`.
- **Documentação Swagger UI Interativa**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Documentação ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📊 Modelos de Dados (Schema JSON)

Os dados retornados seguem a especificação rigorosa definida no arquivo `models.py`.

```json
{
  "metadados": {
    "codigo": "unicamp_2026_q1",
    "edital": "unicamp",
    "numero": 1,
    "tipo_ou_cor": "Q-X",
    "ano": 2026
  },
  "conteudo": {
    "enunciado": "Texto completo do enunciado...",
    "url_img": ["imgs/unicamp_2026_q1_img_1.webp"],
    "dificuldade": null,
    "resolucao": null,
    "dica": null,
    "objetiva": true
  },
  "especificacao": {
    "disciplina": [],
    "assunto": [],
    "topicos": []
  },
  "alternativas": {
    "a": { "texto": "Alternativa A...", "url_img": [], "correta": false },
    "b": { "texto": "Alternativa B...", "url_img": [], "correta": true },
    "c": { "texto": "Alternativa C...", "url_img": [], "correta": false },
    "d": { "texto": "Alternativa D...", "url_img": [], "correta": false },
    "e": null
  }
}
```

---

## 🧪 Execução dos Testes da API

```bash
# Execução padrão via Runner nativo
python test_api.py

# Execução formal via Pytest
python -m pytest -v test_api_pytest.py

# Teste e demonstração com chamadas reais HTTP
python demo_chamada_api.py
```

---

## 🚀 Suporte a Edições
- **Suporte Total Validado:** **2006 até 2026** (1ª Fase e 2ª Fase).
