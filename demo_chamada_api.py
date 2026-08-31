import os
import sys
import requests
import json

# URL base da API FastAPI local
BASE_URL = "http://127.0.0.1:8000"

# Caminhos de exemplo das provas para o teste
PROJETO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Projeto"))
PDF_OBJETIVA = os.path.join(PROJETO_DIR, "Provas", "provas-e-gabaritos-unicamp-2026", "1-fase-unicamp-2026", "prova-q-x-1-fase-unicamp-2026.pdf")
PDF_GABARITO = os.path.join(PROJETO_DIR, "Provas", "provas-e-gabaritos-unicamp-2026", "1-fase-unicamp-2026", "gabarito-q-x-1-fase-unicamp-2026.pdf")
PDF_DISSERTATIVA = os.path.join(PROJETO_DIR, "Provas", "provas-e-gabaritos-unicamp-2026", "2-fase-unicamp-2026", "unicamp-2026-2-fase-prova-dia-1.pdf")

def testar_api_online():
    """Verifica se o servidor FastAPI está ativo."""
    try:
        r = requests.get(f"{BASE_URL}/docs", timeout=3)
        if r.status_code == 200:
            print("✔ Servidor FastAPI está online em http://127.0.0.1:8000\n")
            return True
    except requests.exceptions.RequestException:
        print("❌ Servidor FastAPI não está rodando!")
        print("💡 Para iniciar o servidor, abra outro terminal na pasta Projeto_API e rode:")
        print("   python app.py\n")
        return False

def testar_extrair_objetiva_upload():
    """Testa o endpoint POST /extrair/objetiva enviando os PDFs via upload de arquivo."""
    print("▶ 1. Testando POST /extrair/objetiva (Upload de Arquivo)...")
    url = f"{BASE_URL}/extrair/objetiva"
    
    if not os.path.exists(PDF_OBJETIVA) or not os.path.exists(PDF_GABARITO):
        print(f"⚠️ Arquivo de teste não encontrado: {PDF_OBJETIVA}")
        return

    with open(PDF_OBJETIVA, "rb") as f_prova, open(PDF_GABARITO, "rb") as f_gab:
        files = {
            "prova": ("prova.pdf", f_prova, "application/pdf"),
            "gabarito": ("gabarito.pdf", f_gab, "application/pdf")
        }
        response = requests.post(url, files=files)

    if response.status_code == 200:
        questoes = response.json()
        print(f"  ✔ Sucesso! Total de questões retornadas: {len(questoes)}")
        q1 = questoes[0]
        print(f"  • Questão 1 (Código: {q1['metadados']['codigo']}):")
        print(f"    - Enunciado (início): {q1['conteudo']['enunciado'][:90]}...")
        if q1.get("alternativas"):
            alt_correta = [letra for letra, alt in q1["alternativas"].items() if alt and alt.get("correta")]
            print(f"    - Alternativa correta identificada: {alt_correta}")
    else:
        print(f"  ❌ Erro {response.status_code}: {response.text}")
    print()

def testar_extrair_dissertativa_upload():
    """Testa o endpoint POST /extrair/dissertativa enviando o PDF via upload de arquivo."""
    print("▶ 2. Testando POST /extrair/dissertativa (Upload de Arquivo)...")
    url = f"{BASE_URL}/extrair/dissertativa"
    
    if not os.path.exists(PDF_DISSERTATIVA):
        print(f"⚠️ Arquivo de teste não encontrado: {PDF_DISSERTATIVA}")
        return

    with open(PDF_DISSERTATIVA, "rb") as f_prova:
        files = {
            "prova": ("prova_dissertativa.pdf", f_prova, "application/pdf")
        }
        response = requests.post(url, files=files)

    if response.status_code == 200:
        questoes = response.json()
        print(f"  ✔ Sucesso! Total de questões dissertativas retornadas: {len(questoes)}")
        q1 = questoes[0]
        print(f"  • Questão 1 (Código: {q1['metadados']['codigo']}):")
        print(f"    - Enunciado (início): {q1['conteudo']['enunciado'][:90]}...")
    else:
        print(f"  ❌ Erro {response.status_code}: {response.text}")
    print()

def testar_uso_como_sdk_python():
    """Demonstra o uso da biblioteca como SDK puro (sem servidor web)."""
    print("▶ 3. Testando Uso como Biblioteca Python (SDK Puro)...")
    try:
        import extratorUNICAMP
        if os.path.exists(PDF_OBJETIVA):
            questoes = extratorUNICAMP.objetiva(PDF_OBJETIVA, PDF_GABARITO)
            print(f"  ✔ [SDK] extratorUNICAMP.objetiva(...) extraiu {len(questoes)} questões com sucesso!")
    except Exception as e:
        print(f"  ❌ Erro no SDK: {e}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 SCRIPT DE DEMONSTRAÇÃO E TESTE DA API (Extrator Unicamp)")
    print("=" * 60 + "\n")
    
    # 1. Demonstração via SDK Python
    testar_uso_como_sdk_python()
    
    # 2. Demonstração via Web API REST HTTP
    if testar_api_online():
        testar_extrair_objetiva_upload()
        testar_extrair_dissertativa_upload()
        print("💡 Dica: Você também pode abrir http://127.0.0.1:8000/docs no seu navegador para testar via Swagger!")
