import os
import re
from typing import List

from models import Questao
from extractor import extrair_pdf, extrair_imagens, extrair_texto
from processor import (
    detectar_edital_ano,
    extrair_questoes,
    extrair_questoes_dissertativas,
    extrair_textos_comp,
    mapear_textos_comp,
    enriquecer,
    mapear_imagens_a_questoes_e_alternativas,
    extrair_gabarito,
    aplicar_gabarito,
)
from saver import salvar_questoes, salvar_textos

__all__ = [
    "extrair_prova_objetiva",
    "extrair_prova_dissertativa",
    "extrair_e_salvar_prova_objetiva",
    "extrair_e_salvar_prova_dissertativa",
    "objetiva",
    "dissertativa",
    "salvar_objetiva",
    "salvar_dissertativa",
]

def extrair_prova_objetiva(caminho_prova: str, caminho_gabarito: str = None) -> List[Questao]:
    """
    Extrai em memória as questões objetivas de um PDF de prova.
    Salva as imagens correspondentes no diretório `./imgs` para que os caminhos relativos funcionem.
    """
    edital, ano, tipo_prova = detectar_edital_ano(caminho_prova)
    paginas, doc = extrair_pdf(caminho_prova)
    
    prefixo_img = f"{edital}_{ano}_{tipo_prova.replace('/', '-')}"
    imagens = extrair_imagens(doc, output_dir=os.path.join(".", "imgs"), prefixo=prefixo_img)
    
    texto = extrair_texto(paginas, imagens)
    textos_comp = extrair_textos_comp(texto)
    
    questoes = extrair_questoes(texto, edital=edital, ano=ano, tipo_prova=tipo_prova)
    
    mapa_textos = mapear_textos_comp(textos_comp)
    questoes = enriquecer(questoes, mapa_textos, {})
    mapear_imagens_a_questoes_e_alternativas(questoes, imagens, doc)
    
    if caminho_gabarito and os.path.exists(caminho_gabarito):
        res = extrair_gabarito(caminho_gabarito)
        if isinstance(res, list):
            gabarito_respostas = None
            keys = [k.strip().lower() for k in re.findall(r'[a-zA-Z]', tipo_prova) if k.lower() != 'e']
            for respostas, tipo in res:
                if any(k in tipo.lower() for k in keys):
                    gabarito_respostas = respostas
                    break
            if not gabarito_respostas:
                print(f"[Aviso] Nenhum gabarito correspondente ao tipo '{tipo_prova}' foi encontrado no PDF de gabarito fornecido. As respostas não serão aplicadas.")
            else:
                questoes = aplicar_gabarito(questoes, gabarito_respostas)
        elif isinstance(res, tuple):
            respostas, _ = res
            questoes = aplicar_gabarito(questoes, respostas)
            
    return questoes

def extrair_prova_dissertativa(caminho_prova: str) -> List[Questao]:
    """
    Extrai em memória as questões dissertativas de um PDF de prova.
    Salva as imagens correspondentes no diretório `./imgs` para que os caminhos relativos funcionem.
    """
    edital, ano, tipo_prova = detectar_edital_ano(caminho_prova)
    paginas, doc = extrair_pdf(caminho_prova)
    
    prefixo_img = f"{edital}_{ano}_{tipo_prova.replace('/', '-')}_2fase"
    imagens = extrair_imagens(doc, output_dir=os.path.join(".", "imgs"), prefixo=prefixo_img)
    
    texto = extrair_texto(paginas, imagens)
    textos_comp = extrair_textos_comp(texto)
    
    questoes = extrair_questoes_dissertativas(texto, edital=edital, ano=ano, tipo_prova=tipo_prova)
    
    mapa_textos = mapear_textos_comp(textos_comp)
    questoes = enriquecer(questoes, mapa_textos, {})
    mapear_imagens_a_questoes_e_alternativas(questoes, imagens, doc)
    
    return questoes

def extrair_e_salvar_prova_objetiva(caminho_prova: str, pasta_destino: str, caminho_gabarito: str = None) -> None:
    """
    Extrai as questões objetivas de um PDF de prova e as salva diretamente no disco
    em formato JSON no diretório especificado, junto com a subpasta `imgs`.
    """
    edital, ano, tipo_prova = detectar_edital_ano(caminho_prova)
    paginas, doc = extrair_pdf(caminho_prova)
    
    prefixo_img = f"{edital}_{ano}_{tipo_prova.replace('/', '-')}"
    imagens = extrair_imagens(doc, output_dir=os.path.join(pasta_destino, "imgs"), prefixo=prefixo_img)
    
    texto = extrair_texto(paginas, imagens)
    textos_comp = extrair_textos_comp(texto)
    
    questoes = extrair_questoes(texto, edital=edital, ano=ano, tipo_prova=tipo_prova)
    
    mapa_textos = mapear_textos_comp(textos_comp)
    questoes = enriquecer(questoes, mapa_textos, {})
    mapear_imagens_a_questoes_e_alternativas(questoes, imagens, doc)
    
    if caminho_gabarito and os.path.exists(caminho_gabarito):
        res = extrair_gabarito(caminho_gabarito)
        if isinstance(res, list):
            gabarito_respostas = None
            keys = [k.strip().lower() for k in re.findall(r'[a-zA-Z]', tipo_prova) if k.lower() != 'e']
            for respostas, tipo in res:
                if any(k in tipo.lower() for k in keys):
                    gabarito_respostas = respostas
                    break
            if not gabarito_respostas:
                print(f"[Aviso] Nenhum gabarito correspondente ao tipo '{tipo_prova}' foi encontrado no PDF de gabarito fornecido. As respostas não serão aplicadas.")
            else:
                questoes = aplicar_gabarito(questoes, gabarito_respostas)
        elif isinstance(res, tuple):
            respostas, _ = res
            questoes = aplicar_gabarito(questoes, respostas)
            
    salvar_questoes(questoes, pasta=pasta_destino)
    salvar_textos(textos_comp, pasta=pasta_destino, edital=edital, ano=ano, tipo_ou_cor=tipo_prova)

def extrair_e_salvar_prova_dissertativa(caminho_prova: str, pasta_destino: str) -> None:
    """
    Extrai as questões dissertativas de um PDF de prova e as salva diretamente no disco
    em formato JSON no diretório especificado, junto com a subpasta `imgs`.
    """
    edital, ano, tipo_prova = detectar_edital_ano(caminho_prova)
    paginas, doc = extrair_pdf(caminho_prova)
    
    prefixo_img = f"{edital}_{ano}_{tipo_prova.replace('/', '-')}_2fase"
    imagens = extrair_imagens(doc, output_dir=os.path.join(pasta_destino, "imgs"), prefixo=prefixo_img)
    
    texto = extrair_texto(paginas, imagens)
    textos_comp = extrair_textos_comp(texto)
    
    questoes = extrair_questoes_dissertativas(texto, edital=edital, ano=ano, tipo_prova=tipo_prova)
    
    mapa_textos = mapear_textos_comp(textos_comp)
    questoes = enriquecer(questoes, mapa_textos, {})
    mapear_imagens_a_questoes_e_alternativas(questoes, imagens, doc)
    
    salvar_questoes(questoes, pasta=pasta_destino)
    salvar_textos(textos_comp, pasta=pasta_destino, edital=edital, ano=ano, tipo_ou_cor=tipo_prova)

# Atalhos simples e intuitivos para uso programático da biblioteca
objetiva = extrair_prova_objetiva
dissertativa = extrair_prova_dissertativa
salvar_objetiva = extrair_e_salvar_prova_objetiva
salvar_dissertativa = extrair_e_salvar_prova_dissertativa

