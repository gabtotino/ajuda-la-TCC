# tests/conftest.py
"""Fixtures compartilhadas: app com banco em memória, cliente HTTP e
fábricas de usuários/tarefas.

Cada teste recebe um banco SQLite novo em memória (TestConfig), então os
testes não dependem uns dos outros nem tocam no ajudala.db de desenvolvimento.
"""

import os
import sys
from datetime import date, timedelta

import pytest

# Permite "import app", "import models" etc. rodando pytest da raiz do projeto.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402
from extensions import db as _db  # noqa: E402
from models import Task, User  # noqa: E402

CSRF_TOKEN = "token-csrf-de-teste"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    client = app.test_client()
    # A validação de CSRF continua ativa nos testes: só fixamos um token
    # conhecido na sessão e o enviamos nos formulários.
    with client.session_transaction() as session:
        session["csrf_token"] = CSRF_TOKEN
    return client


@pytest.fixture
def make_user():
    counter = {"n": 0}

    def _make_user(contractor=False, provider=False, name=None, city="São Paulo"):
        counter["n"] += 1
        user = User(
            name=name or f"Usuário {counter['n']}",
            email=f"user{counter['n']}@example.com",
            is_contractor=contractor,
            is_provider=provider,
            city=city,
        )
        user.set_password("senha123")
        _db.session.add(user)
        _db.session.commit()
        return user

    return _make_user


@pytest.fixture
def make_task():
    def _make_task(contractor, **overrides):
        fields = {
            "title": "Lavar carro",
            "description": "Lavar o carro na garagem de casa.",
            "category": "Lavagem de veículo",
            "city": "São Paulo",
            "neighborhood": "Moema",
            "value": 50,
            "desired_date": date.today() + timedelta(days=3),
            "status": Task.STATUS_OPEN,
            "contractor_id": contractor.id,
        }
        fields.update(overrides)
        task = Task(**fields)
        _db.session.add(task)
        _db.session.commit()
        return task

    return _make_task


@pytest.fixture
def login(client):
    def _login(user, password="senha123"):
        return client.post(
            "/auth/login",
            data={"email": user.email, "password": password, "csrf_token": CSRF_TOKEN},
        )

    return _login
