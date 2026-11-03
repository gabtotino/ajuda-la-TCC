# utils.py
"""Funções utilitárias compartilhadas por várias rotas.

Este projeto não usa Flask-WTF (fora do escopo da stack obrigatória), então
a proteção CSRF é implementada manualmente: um token aleatório é gerado uma
vez por sessão, embutido como campo oculto em cada formulário via a função
csrf_token() registrada como global do Jinja2, e conferido no servidor
antes de processar qualquer POST.
"""

import secrets
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import session


def generate_csrf_token():
    """Garante que a sessão tenha um token CSRF e o devolve.

    Chamada pelos templates (registrada em app.py como global do Jinja2),
    então o mesmo token é reaproveitado em todos os formulários de uma
    mesma sessão até ela expirar.
    """
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validate_csrf_token(submitted_token):
    """Confere se o token enviado no formulário bate com o da sessão."""
    expected = session.get("csrf_token")
    if not submitted_token or not expected:
        return False
    # compare_digest evita que o tempo da comparação revele o token.
    return secrets.compare_digest(submitted_token, expected)


def parse_money(raw_value):
    """Converte um valor digitado (aceita '1.234,56', '50,00' ou '50.00')
    em Decimal positivo. Retorna None se não for um valor válido."""
    if not raw_value:
        return None
    raw_value = raw_value.strip().replace("R$", "").strip()
    if "," in raw_value:
        raw_value = raw_value.replace(".", "").replace(",", ".")
    try:
        value = Decimal(raw_value)
    except InvalidOperation:
        return None
    if value <= 0 or value >= Decimal("100000"):
        return None
    return value.quantize(Decimal("0.01"))


def parse_date(raw_value):
    """Converte 'AAAA-MM-DD' (formato do <input type="date">) em date."""
    try:
        return datetime.strptime(raw_value or "", "%Y-%m-%d").date()
    except ValueError:
        return None


def format_date_br(value):
    """Filtro Jinja2: date -> 'seg, 03/11' (ou 'hoje' / 'amanhã')."""
    if not value:
        return ""
    days = (value - date.today()).days
    if days == 0:
        return "hoje"
    if days == 1:
        return "amanhã"
    weekdays = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
    return f"{weekdays[value.weekday()]}, {value.strftime('%d/%m')}"


def time_ago(value):
    """Filtro Jinja2: datetime (UTC) -> 'há 2 horas', 'há 3 dias'..."""
    if not value:
        return ""
    seconds = int((datetime.utcnow() - value).total_seconds())
    if seconds < 60:
        return "agora mesmo"
    minutes = seconds // 60
    if minutes < 60:
        return f"há {minutes} min"
    hours = minutes // 60
    if hours < 24:
        return f"há {hours} hora{'s' if hours > 1 else ''}"
    days = hours // 24
    if days < 30:
        return f"há {days} dia{'s' if days > 1 else ''}"
    months = days // 30
    return f"há {months} {'meses' if months > 1 else 'mês'}"


# Ícone exibido nos cards de tarefa conforme a categoria. Mantido separado
# do model porque é puramente apresentação (não faz sentido morar no banco).
CATEGORY_ICONS = {
    "Lavagem de veículo": "🚗",
    "Limpeza de quintal": "🌿",
    "Mudança": "📦",
    "Montagem de móveis": "🪑",
    "Passeio com pet": "🐕",
    "Pintura": "🎨",
    "Reparos domésticos": "🔧",
    "Limpeza doméstica": "🧹",
    "Aulas particulares": "📚",
    "Outros": "🧰",
}


def category_icon(category):
    """Registrada como filtro Jinja2: {{ task.category|category_icon }}."""
    return CATEGORY_ICONS.get(category, "🧰")


def format_brl(value):
    """Formata um número como moeda brasileira: 1234.5 -> '1.234,50'."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    integer_part, decimal_part = f"{value:,.2f}".split(".")
    integer_part = integer_part.replace(",", ".")
    return f"{integer_part},{decimal_part}"
