# tests/test_auth.py
"""Cadastro, login, logout e proteções básicas de autenticação."""

import pytest

from app import create_app
from config import Config
from models import User
from tests.conftest import CSRF_TOKEN


def test_cadastro_cria_usuario_com_senha_em_hash(client, app):
    response = client.post(
        "/auth/cadastro",
        data={
            "name": "Ana",
            "email": "Ana@Example.com",
            "password": "segredo1",
            "is_provider": "on",
            "csrf_token": CSRF_TOKEN,
        },
    )
    assert response.status_code == 302
    user = User.query.filter_by(email="ana@example.com").one()
    assert user.is_provider and not user.is_contractor
    assert user.password_hash != "segredo1"
    assert user.check_password("segredo1")


def test_cadastro_com_os_dois_papeis(client):
    client.post(
        "/auth/cadastro",
        data={
            "name": "Bia",
            "email": "bia@example.com",
            "password": "segredo1",
            "is_contractor": "on",
            "is_provider": "on",
            "csrf_token": CSRF_TOKEN,
        },
    )
    user = User.query.filter_by(email="bia@example.com").one()
    assert user.is_contractor and user.is_provider


def test_cadastro_exige_pelo_menos_um_papel(client):
    response = client.post(
        "/auth/cadastro",
        data={"name": "Caio", "email": "caio@example.com", "password": "segredo1", "csrf_token": CSRF_TOKEN},
    )
    assert response.status_code == 200
    assert "Escolha pelo menos uma opção" in response.get_data(as_text=True)
    assert User.query.count() == 0


def test_cadastro_recusa_email_duplicado(client, make_user):
    existing = make_user()
    response = client.post(
        "/auth/cadastro",
        data={
            "name": "Outra pessoa",
            "email": existing.email,
            "password": "segredo1",
            "is_contractor": "on",
            "csrf_token": CSRF_TOKEN,
        },
    )
    assert response.status_code == 200
    assert "Já existe uma conta".encode() in response.data
    assert User.query.count() == 1


def test_cadastro_sem_csrf_e_rejeitado(client):
    client.post(
        "/auth/cadastro",
        data={"name": "Ana", "email": "ana@example.com", "password": "segredo1", "is_provider": "on"},
    )
    assert User.query.count() == 0


def test_login_com_senha_errada_falha(client, make_user, login):
    user = make_user()
    response = login(user, password="errada")
    assert "E-mail ou senha inválidos".encode() in response.data
    assert client.get("/painel/").status_code == 302  # continua anônimo


def test_login_redireciona_para_next_interno_mas_nao_externo(client, make_user):
    user = make_user(contractor=True)
    internal = client.post(
        "/auth/login?next=/tarefas/nova",
        data={"email": user.email, "password": "senha123", "csrf_token": CSRF_TOKEN},
    )
    assert internal.headers["Location"].endswith("/tarefas/nova")

    client.post("/auth/logout", data={"csrf_token": CSRF_TOKEN})
    external = client.post(
        "/auth/login?next=//site-malicioso.com",
        data={"email": user.email, "password": "senha123", "csrf_token": CSRF_TOKEN},
    )
    assert "site-malicioso" not in external.headers["Location"]


def test_logout_exige_post_com_csrf(client, make_user, login):
    login(make_user(contractor=True))

    assert client.get("/auth/logout").status_code == 405
    assert client.post("/auth/logout").status_code == 400
    # GET e POST sem token não deslogam: o painel ainda abre normalmente.
    assert "/auth/login" not in client.get("/painel/").headers["Location"]

    response = client.post("/auth/logout", data={"csrf_token": CSRF_TOKEN})
    assert response.status_code == 302
    # Depois do logout, área logada redireciona para o login.
    assert "/auth/login" in client.get("/painel/").headers["Location"]


def test_app_nao_inicia_sem_secret_key():
    class NoSecretConfig(Config):
        SECRET_KEY = None

    with pytest.raises(RuntimeError):
        create_app(NoSecretConfig)
