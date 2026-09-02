# utils.py
"""Funções utilitárias compartilhadas por várias rotas.

Este projeto não usa Flask-WTF (fora do escopo da stack obrigatória), então
a proteção CSRF é implementada manualmente: um token aleatório é gerado uma
vez por sessão, embutido como campo oculto em cada formulário via a função
csrf_token() registrada como global do Jinja2, e conferido no servidor
antes de processar qualquer POST.
"""

import secrets

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
    return submitted_token is not None and submitted_token == session.get("csrf_token")
