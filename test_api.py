import os
import sys
import shutil
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

class APITestSuite:
    def __init__(self):
        self.passes = 0
        self.fails = 0
        self.total = 0
        self.failures_list = []

    def run(self, test_id, desc, test_fn):
        self.total += 1
        print(f"Executando {test_id} - {desc} ... ", end="")
        sys.stdout.flush()
        try:
            test_fn()
            self.passes += 1
            print("PASS")
        except Exception as e:
            self.fails += 1
            print("FAIL")
            print(f"    Erro: {e}")
            self.failures_list.append((test_id, desc, str(e)))

    def report(self):
        print("\n" + "="*40)
        print(f" +------------------------------+")
        print(f" |  RESULTADO API: {self.passes}/{self.total} PASS    |")
        print(f" |  FALHAS:        {self.fails}                |")
        print(f" +------------------------------+")
        print("="*40)
        if self.fails > 0:
            print("\nDetalhes das Falhas:")
            for tid, desc, err in self.failures_list:
                print(f"  [{tid}] {desc}: {err}")
            sys.exit(1)
        else:
            print(f"\nTodos os {self.total} testes da API passaram com sucesso! (Código de saída: 0)")
            sys.exit(0)

def main():
    print("Iniciando testes de validação da API...")
    
    # Garantir caminhos corretos
    for p in [PDF_PATH, GABARITO_PATH, PDF_2FASE_2026_PATH]:
        if not os.path.exists(p):
            print(f"Erro crítico: arquivo de teste não encontrado: {p}")
            sys.exit(1)

    suite = APITestSuite()

    # Limpar qualquer resíduo anterior de imagens locais
    if os.path.exists(os.path.join(BASE_DIR, "imgs")):
        shutil.rmtree(os.path.join(BASE_DIR, "imgs"))

    # 1. Testar extrair_prova_objetiva (em memória)
    def t_api_01():
        questoes = extrair_prova_objetiva(PDF_PATH, GABARITO_PATH)
        assert isinstance(questoes, list), "Retorno deve ser uma lista"
        assert len(questoes) == 72, f"Deveria retornar 72 questões, retornou {len(questoes)}"
        
        # Testar gabarito aplicado
        q46 = next(q for q in questoes if q.metadados.numero == 46)
        assert q46.alternativas.c.correta is True, "Questão 46 deveria ter alternativa C como correta"
        assert q46.alternativas.a.correta is False, "Questão 46 alternativa A deve ser incorreta"
        
        # Verificar se imagens foram extraídas no diretório padrão local
        img_dir = os.path.join(BASE_DIR, "imgs")
        assert os.path.exists(img_dir), "O diretório './imgs' deveria ter sido criado"
        assert len(os.listdir(img_dir)) > 0, "Deveriam ter sido extraídas imagens no diretório local"
    suite.run("API_01", "extrair_prova_objetiva em memória", t_api_01)

    # 2. Testar extrair_prova_dissertativa (em memória)
    def t_api_02():
        questoes = extrair_prova_dissertativa(PDF_2FASE_2026_PATH)
        assert isinstance(questoes, list), "Retorno deve ser uma lista"
        assert len(questoes) == 10, f"Deveria retornar 10 questões, retornou {len(questoes)}"
        
        q1 = next(q for q in questoes if q.metadados.numero == 1)
        assert q1.alternativas is None, "Questão dissertativa não deve ter alternativas"
        assert q1.sub_itens is not None, "Questão dissertativa deve ter sub_itens"
        assert len(q1.sub_itens) == 2, f"Questão 1 deveria ter 2 sub_itens, tem {len(q1.sub_itens)}"
        assert q1.sub_itens[0].letra == "a"
        assert "mecanismo linguístico" in q1.sub_itens[0].texto.lower()
    suite.run("API_02", "extrair_prova_dissertativa em memória", t_api_02)

    # Limpar pastas de destino antes de testar gravação em disco
    pasta_obj = os.path.join(BASE_DIR, "test_api_output_objetiva")
    pasta_diss = os.path.join(BASE_DIR, "test_api_output_dissertativa")
    for folder in [pasta_obj, pasta_diss]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    # 3. Testar extrair_e_salvar_prova_objetiva (disco)
    def t_api_03():
        extrair_e_salvar_prova_objetiva(PDF_PATH, pasta_obj, GABARITO_PATH)
        assert os.path.exists(pasta_obj), "Pasta de destino da objetiva não foi criada"
        
        # Verificar se os JSONs de questões e textos complementares foram criados
        arquivos = os.listdir(pasta_obj)
        questoes_json = [f for f in arquivos if f.endswith(".json") and "COMP" not in f]
        comp_json = [f for f in arquivos if f.endswith(".json") and "COMP" in f]
        
        assert len(questoes_json) == 72, f"Deveria ter salvo 72 JSONs de questões, encontrou {len(questoes_json)}"
        assert len(comp_json) > 0, "Deveria ter salvo JSONs de textos complementares"
        
        # Verificar se a pasta de imagens interna foi criada
        imgs_destino = os.path.join(pasta_obj, "imgs")
        assert os.path.exists(imgs_destino), "A pasta 'imgs' não foi criada dentro de pasta_destino"
        assert len(os.listdir(imgs_destino)) > 0, "Nenhuma imagem foi copiada para a pasta destino"
    suite.run("API_03", "extrair_e_salvar_prova_objetiva em disco", t_api_03)

    # 4. Testar extrair_e_salvar_prova_dissertativa (disco)
    def t_api_04():
        extrair_e_salvar_prova_dissertativa(PDF_2FASE_2026_PATH, pasta_diss)
        assert os.path.exists(pasta_diss), "Pasta de destino da dissertativa não foi criada"
        
        arquivos = os.listdir(pasta_diss)
        questoes_json = [f for f in arquivos if f.endswith(".json") and "COMP" not in f]
        
        assert len(questoes_json) == 10, f"Deveria ter salvo 10 JSONs de questões, encontrou {len(questoes_json)}"
        
        # Verificar imagens
        imgs_destino = os.path.join(pasta_diss, "imgs")
        assert os.path.exists(imgs_destino), "A pasta 'imgs' não foi criada dentro de pasta_destino"
        assert len(os.listdir(imgs_destino)) > 0, "Nenhuma imagem foi copiada para a pasta destino"
    suite.run("API_04", "extrair_e_salvar_prova_dissertativa em disco", t_api_04)

    # Limpeza final das pastas de teste para manter o repositório limpo
    for folder in [pasta_obj, pasta_diss, os.path.join(BASE_DIR, "imgs")]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    suite.report()

if __name__ == "__main__":
    main()
