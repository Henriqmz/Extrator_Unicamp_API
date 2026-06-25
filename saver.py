import os
import json

def salvar_questoes(questoes, pasta):
    os.makedirs(pasta, exist_ok=True)
    for q in questoes:
        edital = q.metadados.edital
        ano = q.metadados.ano
        tipo_ou_cor = q.metadados.tipo_ou_cor.replace("/", "-")
        numero = q.metadados.numero
        nome = os.path.join(pasta, f"{edital}_{ano}_{tipo_ou_cor}_{numero}.json")
        with open(nome, "w", encoding="utf-8") as f:
            json.dump(q.model_dump(), f, ensure_ascii=False, indent=2)

def salvar_textos(textos, pasta, edital="unicamp", ano=2026, tipo_ou_cor="Q-X"):
    os.makedirs(pasta, exist_ok=True)
    tipo_ou_cor_limpo = tipo_ou_cor.replace("/", "-")
    for idx, t in enumerate(textos, 1):
        nome = os.path.join(pasta, f"{edital}_{ano}_{tipo_ou_cor_limpo}_COMP_{idx}.json")
        with open(nome, "w", encoding="utf-8") as f:
            json.dump(t.model_dump(), f, ensure_ascii=False, indent=2)
