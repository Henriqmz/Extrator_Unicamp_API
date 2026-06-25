from pydantic import BaseModel
from typing import Optional, List

__all__ = [
    "AlternativaItem",
    "Metadados",
    "Conteudo",
    "Especificacao",
    "Alternativas",
    "SubItem",
    "Questao",
    "MetadadosComp",
    "ConteudoComp",
    "TextoComplementar",
    "AnaliseQuestaoIA",
    "LoteAnaliseQuestaoIA",
]

class AlternativaItem(BaseModel):
    texto: Optional[str] = None
    url_img: List[str] = []
    correta: bool = False

class Metadados(BaseModel):
    codigo: str
    edital: str
    numero: int
    tipo_ou_cor: str
    ano: int

class Conteudo(BaseModel):
    enunciado: str
    url_img: List[str] = []
    dificuldade: Optional[str] = None
    resolucao: Optional[str] = None
    dica: Optional[List[str]] = None

class Especificacao(BaseModel):
    area: str
    disciplina: List[str]
    assunto: List[str]
    topico: List[str]

class Alternativas(BaseModel):
    a: AlternativaItem
    b: AlternativaItem
    c: AlternativaItem
    d: AlternativaItem
    e: Optional[AlternativaItem] = None

class SubItem(BaseModel):
    letra: str
    texto: str
    url_img: List[str] = []

class Questao(BaseModel):
    metadados: Metadados
    conteudo: Conteudo
    especificacao: Especificacao
    alternativas: Optional[Alternativas] = None
    sub_itens: Optional[List[SubItem]] = None

class MetadadosComp(BaseModel):
    codigos_questoes: List[str]

class ConteudoComp(BaseModel):
    enunciado: str
    img_url: Optional[str] = None

class TextoComplementar(BaseModel):
    metadadosComp: MetadadosComp
    conteudoComp: ConteudoComp

class AnaliseQuestaoIA(BaseModel):
    numero: int
    area: str
    disciplina: List[str]
    assunto: List[str]
    topico: List[str]
    resolucao: str
    dica: List[str]

class LoteAnaliseQuestaoIA(BaseModel):
    questoes: List[AnaliseQuestaoIA]
