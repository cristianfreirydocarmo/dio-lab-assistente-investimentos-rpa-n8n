"""RPA: extrai os clientes da página web e envia ao Webhook do n8n.

Uso:
    pip install -r requirements.txt
    python rpa/extrair_clientes.py          # mensagens estáticas (MVP)
    python rpa/extrair_clientes.py --ia     # mensagens geradas pelo Gemini
"""

import os
import sys

import requests
from bs4 import BeautifulSoup

URL_PAGINA = "https://digitalinnovationone.github.io/dio-lab-assistente-investimentos-rpa-n8n/"

# n8n local (Docker). No n8n Cloud, troque pela Production URL do nó Webhook.
N8N_WEBHOOK = os.getenv("N8N_WEBHOOK", "http://localhost:5678/webhook/clientes")

USAR_IA = "--ia" in sys.argv

# 1) Baixar a página
resposta = requests.get(URL_PAGINA, timeout=30)
resposta.raise_for_status()
resposta.encoding = "utf-8"

# 2) Ler a tabela de clientes
soup = BeautifulSoup(resposta.text, "html.parser")
linhas = soup.select("#clientes tbody tr")

clientes = []

for linha in linhas:
    colunas = linha.find_all("td")

    cliente = {
        "nome": colunas[0].get_text(strip=True),
        "email": colunas[1].get_text(strip=True),
        "saldo": colunas[2].get_text(strip=True),
        "perfil": colunas[3].get_text(strip=True),
    }

    clientes.append(cliente)

# 3) Mostrar o resultado
print(f"Clientes encontrados: {len(clientes)}")
for cliente in clientes:
    print(cliente)

# 4) Enviar a lista "clientes" para o Webhook do n8n via POST
modo = "IA (Gemini)" if USAR_IA else "templates estáticos"
print(f"\nEnviando para {N8N_WEBHOOK} — modo: {modo}...")
if USAR_IA:
    print("(o LLM gera uma mensagem por cliente; pode levar alguns minutos)")

resposta_n8n = requests.post(
    N8N_WEBHOOK,
    json={"clientes": clientes, "usar_ia": USAR_IA},
    timeout=900 if USAR_IA else 60,  # o modo IA faz uma chamada ao LLM por cliente
)
resposta_n8n.raise_for_status()
mensagens = resposta_n8n.json()

# 5) Mostrar as mensagens geradas pelo n8n
print(f"\nMensagens geradas: {len(mensagens)}\n")
for item in mensagens:
    print(f"Para: {item['nome']} <{item['email']}> | {item['perfil']} | {item['saldo']}")
    print(f"Produto recomendado: {item['produto_recomendado']}")
    print(item["mensagem"])
    print("-" * 80)
