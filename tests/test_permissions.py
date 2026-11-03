# tests/test_permissions.py
"""Autorização no servidor: quem pode ver, editar, cancelar e excluir."""

from datetime import date, timedelta

from extensions import db
from models import Application, Message, Review, Task
from tests.conftest import CSRF_TOKEN


def test_anonimo_nao_cria_tarefa(client):
    response = client.get("/tarefas/nova")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_prestador_sem_papel_de_contratante_nao_cria_tarefa(client, make_user, login):
    login(make_user(provider=True))
    response = client.post("/tarefas/nova", data={"title": "x", "csrf_token": CSRF_TOKEN})
    assert response.status_code == 302
    assert Task.query.count() == 0


def test_contratante_cria_tarefa_com_agenda_e_localizacao(client, make_user, login):
    login(make_user(contractor=True))
    response = client.post(
        "/tarefas/nova",
        data={
            "title": "Montar estante",
            "description": "Estante de 5 prateleiras com manual.",
            "category": "Montagem de móveis",
            "city": "São Paulo",
            "neighborhood": "Moema",
            "desired_date": (date.today() + timedelta(days=2)).isoformat(),
            "time_period": "tarde",
            "is_flexible": "on",
            "value": "1.234,50",
            "csrf_token": CSRF_TOKEN,
        },
    )
    assert response.status_code == 302
    task = Task.query.one()
    assert task.neighborhood == "Moema" and task.time_period == "tarde" and task.is_flexible
    assert str(task.value) == "1234.50"


def test_criacao_rejeita_data_no_passado(client, make_user, login):
    login(make_user(contractor=True))
    client.post(
        "/tarefas/nova",
        data={
            "title": "Tarefa",
            "description": "Descrição suficiente aqui.",
            "category": "Outros",
            "city": "São Paulo",
            "neighborhood": "Centro",
            "desired_date": (date.today() - timedelta(days=1)).isoformat(),
            "value": "50",
            "csrf_token": CSRF_TOKEN,
        },
    )
    assert Task.query.count() == 0


def test_outro_usuario_nao_edita_cancela_nem_exclui(client, make_user, make_task, login):
    owner = make_user(contractor=True)
    task = make_task(owner)
    login(make_user(contractor=True))

    assert client.get(f"/tarefas/{task.id}/editar").status_code == 403
    assert client.post(f"/tarefas/{task.id}/cancelar", data={"csrf_token": CSRF_TOKEN}).status_code == 403
    assert client.post(f"/tarefas/{task.id}/excluir", data={"csrf_token": CSRF_TOKEN}).status_code == 403
    assert db.session.get(Task, task.id).status == Task.STATUS_OPEN


def test_listagem_publica_mostra_so_tarefas_abertas(client, make_user, make_task):
    owner = make_user(contractor=True)
    make_task(owner, title="Tarefa aberta visível")
    make_task(owner, title="Tarefa concluída escondida", status=Task.STATUS_DONE)
    make_task(owner, title="Tarefa cancelada escondida", status=Task.STATUS_CANCELED)

    html = client.get("/tarefas/").get_data(as_text=True)
    assert "Tarefa aberta visível" in html
    assert "concluída escondida" not in html
    assert "cancelada escondida" not in html


def test_detalhe_de_tarefa_encerrada_so_para_envolvidos(client, make_user, make_task, login):
    owner = make_user(contractor=True)
    provider = make_user(provider=True)
    outsider = make_user(provider=True)
    task = make_task(owner, status=Task.STATUS_DONE, accepted_provider_id=provider.id)

    assert client.get(f"/tarefas/{task.id}").status_code == 404  # anônimo

    login(outsider)
    assert client.get(f"/tarefas/{task.id}").status_code == 404
    client.post("/auth/logout", data={"csrf_token": CSRF_TOKEN})

    login(provider)
    assert client.get(f"/tarefas/{task.id}").status_code == 200
    client.post("/auth/logout", data={"csrf_token": CSRF_TOKEN})

    login(owner)
    assert client.get(f"/tarefas/{task.id}").status_code == 200


def test_excluir_tarefa_remove_candidaturas_mensagens_e_avaliacao(client, make_user, make_task, login):
    owner = make_user(contractor=True)
    provider = make_user(provider=True)
    task = make_task(owner, status=Task.STATUS_CANCELED)
    db.session.add_all([
        Application(task_id=task.id, provider_id=provider.id, message="Posso ajudar com isso."),
        Message(task_id=task.id, sender_id=owner.id, content="Olá!"),
        Review(task_id=task.id, reviewer_id=owner.id, reviewed_id=provider.id, rating=5),
    ])
    db.session.commit()

    login(owner)
    response = client.post(f"/tarefas/{task.id}/excluir", data={"csrf_token": CSRF_TOKEN})
    assert response.status_code == 302
    assert Task.query.count() == 0
    assert Application.query.count() == 0
    assert Message.query.count() == 0
    assert Review.query.count() == 0


def test_nao_exclui_tarefa_em_andamento(client, make_user, make_task, login):
    owner = make_user(contractor=True)
    provider = make_user(provider=True)
    task = make_task(owner, status=Task.STATUS_IN_PROGRESS, accepted_provider_id=provider.id)

    login(owner)
    client.post(f"/tarefas/{task.id}/excluir", data={"csrf_token": CSRF_TOKEN})
    assert db.session.get(Task, task.id) is not None


def test_filtros_por_cidade_e_faixa_de_valor(client, make_user, make_task):
    owner = make_user(contractor=True)
    make_task(owner, title="Barata em Osasco", city="Osasco", value=30)
    make_task(owner, title="Cara em Osasco", city="Osasco", value=300)
    make_task(owner, title="Em São Paulo", city="São Paulo", value=40)

    html = client.get("/tarefas/?cidade=Osasco&valor_max=100").get_data(as_text=True)
    assert "Barata em Osasco" in html
    assert "Cara em Osasco" not in html
    assert "Em São Paulo" not in html


def test_ordenacao_por_menor_valor(client, make_user, make_task):
    owner = make_user(contractor=True)
    make_task(owner, title="Tarefa de 90", value=90)
    make_task(owner, title="Tarefa de 20", value=20)

    html = client.get("/tarefas/?ordem=menor_valor").get_data(as_text=True)
    assert html.index("Tarefa de 20") < html.index("Tarefa de 90")


def test_paginas_de_erro_customizadas(client, make_user, make_task, login):
    assert "Página não encontrada" in client.get("/nao-existe").get_data(as_text=True)

    task = make_task(make_user(contractor=True))
    login(make_user(contractor=True))
    forbidden = client.get(f"/tarefas/{task.id}/editar")
    assert forbidden.status_code == 403
    assert "Acesso negado" in forbidden.get_data(as_text=True)
