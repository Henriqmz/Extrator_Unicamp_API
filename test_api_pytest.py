import os
import shutil
import pytest
from extratorUNICAMP import (
    extrair_prova_objetiva,
    extrair_prova_dissertativa,
    extrair_e_salvar_prova_objetiva,
    extrair_e_salvar_prova_dissertativa,
)
from models import Questao

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PDF_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "Projeto", "Provas", "provas-e-gabaritos-unicamp-2026", "1-fase-unicamp-2026", "prova-q-x-1-fase-unicamp-2026.pdf"))
GABARITO_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "Projeto", "Provas", "provas-e-gabaritos-unicamp-2026", "1-fase-unicamp-2026", "gabarito-q-x-1-fase-unicamp-2026.pdf"))
PDF_2FASE_2026_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "Projeto", "Provas", "provas-e-gabaritos-unicamp-2026", "2-fase-unicamp-2026", "unicamp-2026-2-fase-prova-dia-1.pdf"))

@pytest.fixture(scope="session", autouse=True)
def cleanup():
    # Setup: clean temporary folders
    for folder in [os.path.join(BASE_DIR, "imgs"), os.path.join(BASE_DIR, "test_api_pytest_objetiva"), os.path.join(BASE_DIR, "test_api_pytest_dissertativa")]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    yield
    # Teardown: clean test output folders
    for folder in [os.path.join(BASE_DIR, "imgs"), os.path.join(BASE_DIR, "test_api_pytest_objetiva"), os.path.join(BASE_DIR, "test_api_pytest_dissertativa")]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

def test_api_01_extrair_prova_objetiva_memoria():
    questoes = extrair_prova_objetiva(PDF_PATH, GABARITO_PATH)
    assert isinstance(questoes, list)
    assert len(questoes) == 72
    q46 = next(q for q in questoes if q.metadados.numero == 46)
    assert q46.alternativas.c.correta is True
    assert q46.alternativas.a.correta is False
    img_dir = os.path.join(BASE_DIR, "imgs")
    assert os.path.exists(img_dir)
    assert len(os.listdir(img_dir)) > 0

def test_api_02_extrair_prova_dissertativa_memoria():
    questoes = extrair_prova_dissertativa(PDF_2FASE_2026_PATH)
    assert isinstance(questoes, list)
    assert len(questoes) == 10
    q1 = next(q for q in questoes if q.metadados.numero == 1)
    assert q1.alternativas is None
    assert "a)" in q1.conteudo.enunciado
    assert "b)" in q1.conteudo.enunciado
    assert "mecanismo linguístico" in q1.conteudo.enunciado.lower()

def test_api_03_extrair_e_salvar_prova_objetiva_disco():
    pasta_obj = os.path.join(BASE_DIR, "test_api_pytest_objetiva")
    if os.path.exists(pasta_obj):
        shutil.rmtree(pasta_obj)
    extrair_e_salvar_prova_objetiva(PDF_PATH, pasta_obj, GABARITO_PATH)
    assert os.path.exists(pasta_obj)
    arquivos = os.listdir(pasta_obj)
    questoes_json = [f for f in arquivos if f.endswith(".json") and "COMP" not in f]
    comp_json = [f for f in arquivos if f.endswith(".json") and "COMP" in f]
    assert len(questoes_json) == 72
    assert len(comp_json) > 0
    imgs_destino = os.path.join(pasta_obj, "imgs")
    assert os.path.exists(imgs_destino)
    assert len(os.listdir(imgs_destino)) > 0

def test_api_04_extrair_e_salvar_prova_dissertativa_disco():
    pasta_diss = os.path.join(BASE_DIR, "test_api_pytest_dissertativa")
    if os.path.exists(pasta_diss):
        shutil.rmtree(pasta_diss)
    extrair_e_salvar_prova_dissertativa(PDF_2FASE_2026_PATH, pasta_diss)
    assert os.path.exists(pasta_diss)
    arquivos = os.listdir(pasta_diss)
    questoes_json = [f for f in arquivos if f.endswith(".json") and "COMP" not in f]
    assert len(questoes_json) == 10
    imgs_destino = os.path.join(pasta_diss, "imgs")
    assert os.path.exists(imgs_destino)
    assert len(os.listdir(imgs_destino)) > 0
