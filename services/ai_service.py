# services/ai_service.py
"""Integração com a OpenAI API: transforma uma descrição livre da tarefa
em campos estruturados (título, descrição, categoria, valor sugerido).
"""

import json

from openai import OpenAI

from config import Config
from models import Task

MODEL_NAME = "gpt-4o-mini"

# Prompt de sistema com few-shot examples: mostrar 3 exemplos de
# entrada/saída deixa o formato da resposta muito mais consistente do que
# só descrever as regras em texto.
SYSTEM_PROMPT = """Você é um assistente que ajuda contratantes da plataforma Ajuda-Lá a
transformar uma descrição livre em uma tarefa estruturada.

Categorias válidas (use exatamente um destes valores): {categories}.

Responda SEMPRE com um JSON válido, e nada além do JSON, neste formato exato:
{{"titulo": "...", "descricao": "...", "categoria": "...", "valor_sugerido": 00.00}}

Regras:
- "titulo": curto e claro (no máximo 8 palavras).
- "descricao": reescreva o pedido do usuário de forma organizada e educada, em português.
- "categoria": escolha a categoria da lista que melhor combina. Se nenhuma combinar
  bem, use "Outros".
- "valor_sugerido": um número (sem "R$" e sem texto). Se o usuário não mencionar
  valor, sugira um valor razoável de mercado para esse tipo de tarefa no Brasil.

Exemplos:

Usuário: "preciso lavar meu carro no sábado, pago 50 reais"
Resposta: {{"titulo": "Lavar carro no sábado", "descricao": "Preciso lavar meu carro no sábado.", "categoria": "Lavagem de veículo", "valor_sugerido": 50.00}}

Usuário: "alguém pra passear com meu cachorro todo fim de tarde essa semana"
Resposta: {{"titulo": "Passear com cachorro à tarde", "descricao": "Preciso de alguém para passear com meu cachorro no fim da tarde, durante a semana.", "categoria": "Passeio com pet", "valor_sugerido": 30.00}}

Usuário: "montar um guarda roupa novo que comprei"
Resposta: {{"titulo": "Montar guarda-roupa novo", "descricao": "Comprei um guarda-roupa novo e preciso de ajuda para montá-lo.", "categoria": "Montagem de móveis", "valor_sugerido": 90.00}}
""".format(categories=", ".join(Task.CATEGORIES))


class AIServiceError(Exception):
    """Erro ao chamar a API da OpenAI ou ao interpretar a resposta dela.

    As rotas capturam esta exceção e devolvem uma mensagem de erro amigável
    para o frontend, que então deixa o usuário preencher o formulário
    manualmente — o fallback exigido pela especificação da Etapa 11.
    """


def parse_task_description(free_text):
    """Chama a OpenAI API e devolve um dicionário com os campos da tarefa."""
    if not Config.OPENAI_API_KEY:
        raise AIServiceError(
            "Assistente de IA não configurado (defina OPENAI_API_KEY no arquivo .env)."
        )

    client = OpenAI(api_key=Config.OPENAI_API_KEY)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": free_text},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
    except Exception as exc:  # a chamada de rede pode falhar de várias formas
        raise AIServiceError(f"Falha ao consultar a IA: {exc}") from exc

    raw_content = response.choices[0].message.content
    try:
        data = json.loads(raw_content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise AIServiceError("A IA respondeu em um formato inesperado.") from exc

    category = data.get("categoria")
    if category not in Task.CATEGORIES:
        category = "Outros"

    try:
        value = round(float(data.get("valor_sugerido", 0)), 2)
    except (TypeError, ValueError):
        value = None

    return {
        "titulo": (data.get("titulo") or "").strip()[:150],
        "descricao": (data.get("descricao") or "").strip(),
        "categoria": category,
        "valor_sugerido": value,
    }
