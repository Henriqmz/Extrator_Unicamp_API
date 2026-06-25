# Projeto API - Extrator de Provas do Vestibular

Este módulo fornece uma API programática em Python para extrair de forma estruturada as questões do vestibular (como Unicamp), cobrindo tanto a **1ª Fase (Objetiva)** quanto a **2ª Fase (Dissertativa)**.

## 📦 Instalação

Agora o projeto está configurado como um pacote Python instalável padrão. Ao instalá-lo, o **`pip` baixará e configurará automaticamente todas as dependências necessárias** (como PyMuPDF, Pillow, Pydantic, FastAPI, Uvicorn e Multipart).

### Como Instalar Localmente (Modo Desenvolvimento)
Navegue até a pasta `Projeto_API` no seu terminal e execute:
```bash
pip install -e .
```
*(O parâmetro `-e` indica modo "editável", o que significa que qualquer alteração que você fizer nos arquivos de código da pasta será refletida imediatamente no ambiente de quem importá-lo!).*

### Como Instalar diretamente do Git (GitHub)
Caso você suba esta pasta para um repositório Git, qualquer pessoa poderá instalar sua biblioteca rodando:
```bash
pip install git+https://github.com/seu-usuario/seu-repositorio.git#subdirectory=Projeto_API
```


## Como Importar e Utilizar

A biblioteca é extremamente simples e intuitiva de usar. Após a instalação, você pode importar os atalhos simplificados diretamente do módulo:

```python
import extratorUNICAMP

# 1. Extração em Memória (Retorna lista de objetos Questao)
questoes_obj = extratorUNICAMP.objetiva("prova.pdf", "gabarito.pdf")
questoes_dis = extratorUNICAMP.dissertativa("prova_dis.pdf")

# 2. Extração e Gravação em Disco (Salva JSONs e imagens)
extratorUNICAMP.salvar_objetiva("prova.pdf", "pasta_destino", "gabarito.pdf")
extratorUNICAMP.salvar_dissertativa("prova_dis.pdf", "pasta_destino")
```

*(Nota: Os nomes descritivos longos originais como `extrair_prova_objetiva` e `extrair_e_salvar_prova_dissertativa` também continuam disponíveis para importação se você preferir).*

---

### 1. Extração em Memória


#### Prova Objetiva (1ª Fase)
Retorna uma lista de objetos do modelo `Questao` com gabarito associado (se fornecido).
```python
questoes = extrair_prova_objetiva(
    caminho_prova="caminho/para/prova_1fase.pdf",
    caminho_gabarito="caminho/para/gabarito_1fase.pdf" # opcional
)

for questao in questoes:
    print(f"Questão {questao.metadados.numero}: {questao.conteudo.enunciado[:100]}...")
```

#### Prova Dissertativa (2ª Fase)
Retorna uma lista de objetos do modelo `Questao` estruturados com sub-itens discursivos (a, b).
```python
questoes = extrair_prova_dissertativa("caminho/para/prova_2fase.pdf")

for questao in questoes:
    print(f"Questão {questao.metadados.numero}:")
    for sub in questao.sub_itens:
        print(f"  Sub-item {sub.letra}): {sub.texto[:80]}...")
```

*Nota: As funções em memória salvam temporariamente as imagens extraídas no subdiretório local `./imgs` para manter os caminhos relativos funcionais.*

---

### 2. Extração com Gravação Direta em Disco

Salva cada questão individualmente como um arquivo JSON no diretório de destino fornecido, junto com uma pasta `imgs` contendo as imagens da prova associadas às questões.

#### Salvar Prova Objetiva (1ª Fase)
```python
extrair_e_salvar_prova_objetiva(
    caminho_prova="caminho/para/prova.pdf",
    pasta_destino="saida_prova_objetiva",
    caminho_gabarito="caminho/para/gabarito.pdf" # opcional
)
```

#### Salvar Prova Dissertativa (2ª Fase)
```python
extrair_e_salvar_prova_dissertativa(
    caminho_prova="caminho/para/prova_2fase.pdf",
    pasta_destino="saida_prova_dissertativa"
)
```

---

## Modelos de Dados (Schemas)

Os dados retornados seguem a especificação rigorosa definida no arquivo `models.py`.

```python
from models import Questao, Alternativas, AlternativaItem, SubItem, Metadados, Conteudo, Especificacao
```

### Formato JSON Gerado (Exemplo Dissertativa)
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
    "enunciado": "Texto da questão...",
    "url_img": [],
    "dificuldade": null,
    "resolucao": null,
    "dica": null
  },
  "especificacao": {
    "area": "desconhecida",
    "disciplina": [],
    "assunto": [],
    "topico": []
  },
  "alternativas": null,
  "sub_itens": [
    {
      "letra": "a",
      "texto": "Texto do sub-item a...",
      "url_img": []
    },
    {
      "letra": "b",
      "texto": "Texto do sub-item b...",
      "url_img": []
    }
  ]
}
```

---

## ⚡ Execução como Web API (FastAPI)

O projeto também vem com um servidor web wrapper baseado em **FastAPI** pronto para rodar, permitindo o recebimento de PDFs de provas por upload HTTP e fornecendo uma interface de documentação automática e interativa (Swagger UI).

### Instalação dos Requisitos da Web API
```bash
pip install fastapi uvicorn python-multipart
```

### Executar o Servidor
Navegue até a pasta `Projeto_API` e execute o arquivo `app.py`:
```bash
python app.py
```
O servidor será iniciado localmente em `http://127.0.0.1:8000`.

### Acessar a Documentação Interativa (Swagger)
Abra o seu navegador e acesse:
* **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (permite testar requisições diretamente do navegador).
* **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc).
