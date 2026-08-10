# Projeto API - Extrator de Provas do Vestibular UNICAMP

Este módulo fornece uma API programática em Python e Web API (FastAPI) para extrair de forma estruturada as questões do vestibular UNICAMP (**editações de 2006 até 2026**), cobrindo tanto a **1ª Fase (Objetiva e Discursiva)** quanto a **2ª Fase (Dissertativa)**.

---

## 📦 Instalação

O projeto está configurado como um pacote Python instalável padrão (`setup.py`). Ao instalá-lo, o `pip` baixará e configurará automaticamente todas as dependências (PyMuPDF, Pillow, Pydantic, FastAPI, Uvicorn e Multipart).

### Como Instalar Localmente (Modo Desenvolvimento)
Navegue até a pasta `Projeto_API` no seu terminal e execute:
```bash
pip install -e .
```

---

## 💻 Como Importar e Utilizar

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

## 📊 Modelos de Dados (Schema JSON Atualizado)

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

## 🚀 Suporte a Edições
- **Suporte Total Validado:** **2006 até 2026** (1ª Fase e 2ª Fase).

---

## ⚡ Execução como Web API (FastAPI)

Navegue até a pasta `Projeto_API` e execute o arquivo `app.py`:
```bash
python app.py
```
O servidor será iniciado em `http://127.0.0.1:8000`.
- **Documentação Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
