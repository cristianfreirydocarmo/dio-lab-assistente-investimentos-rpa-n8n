"""Gera n8n/workflow.json a partir de n8n/cruzar_perfis.js.

Uso: python n8n/build_workflow.py
Depois importe o workflow.json no n8n (menu ... > Import from File).
"""

import json
from pathlib import Path

PASTA = Path(__file__).parent
URL_CSV = "https://digitalinnovationone.github.io/dio-lab-assistente-investimentos-rpa-n8n/data.csv"

MODELO_GEMINI = "models/gemini-3.5-flash-lite"

NO_CRUZAR = "Cruzar Perfil x Investimentos"
NO_TEMPLATE = "Mensagem Estática (Template)"
CLIENTE = f"$('{NO_CRUZAR}').item.json"  # dados do cliente já cruzados

# Templates fixos do MVP: (abertura, frase das alternativas, fechamento) por perfil.
TEMPLATES = {
    "Conservador": (
        "Como seu perfil é Conservador, nosso foco é segurança e renda fixa.",
        "Outras opções seguras para você:",
        "Seu dinheiro protegido e rendendo com tranquilidade.",
    ),
    "Moderado": (
        "Seu perfil Moderado pede um mix equilibrado entre renda fixa e variável.",
        "Para diversificar, considere também:",
        "Equilíbrio entre segurança e crescimento.",
    ),
    "Arrojado": (
        "Com seu perfil Arrojado, o foco é ações e maior potencial de retorno.",
        "Para ampliar sua carteira:",
        "Lembre-se: maior potencial de retorno vem com maior risco.",
    ),
}


def _expressao_template(abertura, alternativas, fechamento):
    return (
        f"'Olá, ' + $json.primeiro_nome + '! {abertura} Com seu saldo de ' + $json.saldo + "
        f"', recomendamos ' + $json.recomendacao_texto + '. ' + "
        f"($json.alternativas.length ? '{alternativas} ' + $json.alternativas_texto + '. ' : '') + "
        f"'{fechamento}'"
    )


TEMPLATE_ESTATICO = (
    "={{ ({\n"
    + ",\n".join(f"  '{perfil}': {_expressao_template(*partes)}" for perfil, partes in TEMPLATES.items())
    + "\n})[$json.perfil] ?? ('Olá, ' + $json.primeiro_nome + '! Não identificamos seu perfil de investidor. "
    "Que tal refazer seu questionário de perfil para você receber a melhor recomendação?') }}"
)

PROMPT_USUARIO = """=Cliente: {{ $json.nome }}
Perfil de investidor: {{ $json.perfil }}
Saldo disponível: {{ $json.saldo }}
Produto recomendado pela regra da casa: {{ $json.recomendacao_texto }}
Outras opções elegíveis para o saldo: {{ $json.alternativas_texto }}
Todos os produtos do perfil: {{ $json.produtos_do_perfil }}

Escreva a mensagem de recomendação para este cliente."""

PROMPT_SISTEMA = """Você é o assistente de relacionamento de uma corretora de investimentos e escreve mensagens curtas e personalizadas para clientes.

Regras:
- Escreva em português do Brasil, tratando o cliente pelo primeiro nome.
- Entre 60 e 110 palavras, em texto corrido, sem markdown, sem emojis e sem assinatura.
- Ajuste o tom ao perfil: Conservador = segurança e renda fixa; Moderado = equilíbrio entre renda fixa e variável; Arrojado = ações e maior potencial de retorno, deixando claro o risco.
- Considere o saldo do cliente: explique em uma frase por que o produto recomendado faz sentido para esse valor.
- Cite apenas produtos e números que aparecem nos dados recebidos, escritos em algarismos como nos dados (ex.: R$ 1.000,00 e 14.0%). Nunca invente taxas, prazos ou promessas de ganho, e não use palavras como "garante" ou "garantido" ao falar de rentabilidade.
- Termine com um convite para conversar com um especialista e a frase: "Rentabilidade passada não garante rentabilidade futura.\""""


def no(nome, tipo, versao, posicao, parametros, **extra):
    return {
        "parameters": parametros,
        "id": extra.pop("id"),
        "name": nome,
        "type": tipo,
        "typeVersion": versao,
        "position": posicao,
        **extra,
    }


def atribuicao(id_, nome, valor, tipo="string"):
    return {"id": id_, "name": nome, "value": valor, "type": tipo}


def campos_saida(origem_cliente, mensagem, origem_mensagem):
    """Campos finais devolvidos ao script Python."""
    c = origem_cliente
    return {
        "assignments": {
            "assignments": [
                atribuicao("a1", "nome", f"={{{{ {c}.nome }}}}"),
                atribuicao("a2", "email", f"={{{{ {c}.email }}}}"),
                atribuicao("a3", "perfil", f"={{{{ {c}.perfil }}}}"),
                atribuicao("a4", "saldo", f"={{{{ {c}.saldo }}}}"),
                atribuicao("a5", "produto_recomendado", f"={{{{ {c}.produto_recomendado }}}}"),
                atribuicao("a6", "alternativas", f"={{{{ {c}.alternativas }}}}", "array"),
                atribuicao("a7", "mensagem", mensagem),
                atribuicao("a8", "origem_mensagem", origem_mensagem),
            ]
        },
        "options": {},
    }


def montar():
    codigo = (PASTA / "cruzar_perfis.js").read_text(encoding="utf-8")

    nodes = [
        no("Webhook - Receber Clientes", "n8n-nodes-base.webhook", 2.1, [0, 300],
           {"httpMethod": "POST", "path": "clientes", "responseMode": "responseNode", "options": {}},
           id="0b6f0d0e-1a11-4c55-9a01-000000000001",
           webhookId="7d1c3a52-5f0e-4b8e-9d36-2c9a4e1b0a01"),
        no("Baixar data.csv", "n8n-nodes-base.httpRequest", 4.5, [220, 300],
           {"url": URL_CSV,
            "options": {"response": {"response": {"responseFormat": "file"}}}},
           id="0b6f0d0e-1a11-4c55-9a01-000000000002"),
        no("Ler CSV de Investimentos", "n8n-nodes-base.extractFromFile", 1.1, [440, 300],
           {"options": {}},
           id="0b6f0d0e-1a11-4c55-9a01-000000000003"),
        no(NO_CRUZAR, "n8n-nodes-base.code", 2, [660, 300],
           {"jsCode": codigo},
           id="0b6f0d0e-1a11-4c55-9a01-000000000004"),
        # O template é sempre gerado: é a resposta do MVP e o fallback se a IA falhar.
        no(NO_TEMPLATE, "n8n-nodes-base.set", 3.4, [880, 300],
           campos_saida("$json", TEMPLATE_ESTATICO, "template"),
           id="0b6f0d0e-1a11-4c55-9a01-000000000009"),
        no("Usar IA?", "n8n-nodes-base.if", 2.3, [1100, 300],
           {"conditions": {
               "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
               "conditions": [{
                   "id": "c1",
                   "leftValue": f"={{{{ {CLIENTE}.usar_ia }}}}",
                   "rightValue": "",
                   "operator": {"type": "boolean", "operation": "true", "singleValue": True},
               }],
               "combinator": "and",
           }, "looseTypeValidation": True, "options": {}},
           id="0b6f0d0e-1a11-4c55-9a01-000000000005"),
        no("Agente de IA - Mensagem Personalizada", "@n8n/n8n-nodes-langchain.agent", 3.1, [1340, 0],
           {"promptType": "define", "text": PROMPT_USUARIO.replace("$json", CLIENTE),
            "options": {
                "systemMessage": PROMPT_SISTEMA,
                # Uma chamada a cada 6 s: respeita o limite por minuto do plano gratuito.
                "batching": {"batchSize": 1, "delayBetweenBatches": 6000},
            }},
           id="0b6f0d0e-1a11-4c55-9a01-000000000006",
           retryOnFail=True, maxTries=3, waitBetweenTries=5000, onError="continueRegularOutput"),
        no("Google Gemini Chat Model", "@n8n/n8n-nodes-langchain.lmChatGoogleGemini", 1.1, [1340, 200],
           {"modelName": MODELO_GEMINI, "options": {"temperature": 0.7}},
           id="0b6f0d0e-1a11-4c55-9a01-000000000007"),
        no("Formatar Resposta da IA", "n8n-nodes-base.set", 3.4, [1660, 0],
           campos_saida(
               CLIENTE,
               f"={{{{ $json.output ? $json.output.trim() : $('{NO_TEMPLATE}').item.json.mensagem }}}}",
               "={{ $json.output ? 'ia_gemini' : 'template_fallback' }}",
           ),
           id="0b6f0d0e-1a11-4c55-9a01-000000000008"),
        no("Responder ao Webhook", "n8n-nodes-base.respondToWebhook", 1.5, [1900, 300],
           {"respondWith": "allIncomingItems", "options": {}},
           id="0b6f0d0e-1a11-4c55-9a01-00000000000a"),
    ]

    def liga(destino, indice=0):
        return {"node": destino, "type": "main", "index": indice}

    connections = {
        "Webhook - Receber Clientes": {"main": [[liga("Baixar data.csv")]]},
        "Baixar data.csv": {"main": [[liga("Ler CSV de Investimentos")]]},
        "Ler CSV de Investimentos": {"main": [[liga(NO_CRUZAR)]]},
        NO_CRUZAR: {"main": [[liga(NO_TEMPLATE)]]},
        NO_TEMPLATE: {"main": [[liga("Usar IA?")]]},
        "Usar IA?": {"main": [
            [liga("Agente de IA - Mensagem Personalizada")],
            [liga("Responder ao Webhook")],
        ]},
        "Agente de IA - Mensagem Personalizada": {"main": [[liga("Formatar Resposta da IA")]]},
        "Google Gemini Chat Model": {"ai_languageModel": [[
            {"node": "Agente de IA - Mensagem Personalizada", "type": "ai_languageModel", "index": 0}
        ]]},
        "Formatar Resposta da IA": {"main": [[liga("Responder ao Webhook")]]},
    }

    return {
        "name": "Assistente de Investimentos (RPA + IA)",
        "nodes": nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1", "timezone": "America/Sao_Paulo"},
        "pinData": {},
        "active": False,
        "id": "AssistInvestRPA01",
    }


if __name__ == "__main__":
    destino = PASTA / "workflow.json"
    destino.write_text(json.dumps(montar(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Gerado: {destino}")
