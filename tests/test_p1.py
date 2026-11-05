# tests/test_p1.py
"""Chat, upload de imagens, tarefas salvas, alertas e painéis (P1)."""

import os
from datetime import datetime, timedelta
from io import BytesIO

from extensions import db
from models import Alert, Message, SavedTask, Task, TaskImage, User
from services.notifications import navigation_badges
from tests.conftest import CSRF_TOKEN

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 200


def logout(client):
    client.post("/auth/logout", data={"csrf_token": CSRF_TOKEN})


def task_form(**overrides):
    data = {
        "title": "Montar estante",
        "description": "Estante de 5 prateleiras com manual.",
        "category": "Montagem de móveis",
        "city": "São Paulo",
        "neighborhood": "Moema",
        "desired_date": (datetime.utcnow().date() + timedelta(days=2)).isoformat(),
        "time_period": "tarde",
        "value": "80,00",
        "csrf_token": CSRF_TOKEN,
    }
    data.update(overrides)
    return data


def image(name="foto.png", content=PNG_BYTES, mimetype="image/png"):
    return (BytesIO(content), name, mimetype)


def upload_dir(app):
    return app.config["UPLOAD_FOLDER"]


# ============================================================== chat

def chat_setup(make_user, make_task):
    owner = make_user(contractor=True, name="Contratante")
    provider = make_user(provider=True, name="Prestador")
    task = make_task(owner, status=Task.STATUS_IN_PROGRESS, accepted_provider_id=provider.id)
    return owner, provider, task


def send(client, task, content="Posso chegar às 9h?", token=CSRF_TOKEN):
    return client.post(f"/mensagens/tarefa/{task.id}/api", json={"content": content, "csrf_token": token})


def test_chat_so_para_contratante_e_prestador_escolhido(client, make_user, make_task, login):
    owner, provider, task = chat_setup(make_user, make_task)
    outsider = make_user(provider=True)

    assert "/auth/login" in client.get(f"/mensagens/tarefa/{task.id}").headers["Location"]

    login(outsider)
    assert client.get(f"/mensagens/tarefa/{task.id}").status_code == 403
    assert send(client, task).status_code == 403
    logout(client)

    login(provider)
    assert client.get(f"/mensagens/tarefa/{task.id}").status_code == 200
    assert send(client, task).status_code == 201
    logout(client)

    login(owner)
    assert client.get(f"/mensagens/tarefa/{task.id}").status_code == 200
    assert Message.query.count() == 1


def test_chat_indisponivel_antes_do_aceite(client, make_user, make_task, login):
    owner = make_user(contractor=True)
    task = make_task(owner)  # aberta, sem prestador escolhido
    login(owner)
    assert client.get(f"/mensagens/tarefa/{task.id}").status_code == 403


def test_chat_valida_conteudo_e_csrf(client, make_user, make_task, login):
    _, provider, task = chat_setup(make_user, make_task)
    login(provider)

    assert send(client, task, content="   ").status_code == 400
    assert send(client, task, content="x" * 1001).status_code == 400
    assert send(client, task, token="errado").status_code == 400
    assert Message.query.count() == 0


def test_chat_somente_leitura_apos_conclusao(client, make_user, make_task, login):
    owner, provider, task = chat_setup(make_user, make_task)
    db.session.add(Message(task_id=task.id, sender_id=provider.id, content="Feito!"))
    task.status = Task.STATUS_DONE
    db.session.commit()

    login(owner)
    assert client.get(f"/mensagens/tarefa/{task.id}").status_code == 200
    response = send(client, task)
    assert response.status_code == 403
    assert Message.query.count() == 1


def test_polling_retorna_so_novas_e_marca_como_lidas(client, make_user, make_task, login):
    owner, provider, task = chat_setup(make_user, make_task)
    first = Message(task_id=task.id, sender_id=provider.id, content="Oi!")
    second = Message(task_id=task.id, sender_id=provider.id, content="Tudo certo?")
    db.session.add_all([first, second])
    db.session.commit()

    assert navigation_badges(db.session.get(User, owner.id))["messages"] == 2

    login(owner)
    data = client.get(f"/mensagens/tarefa/{task.id}/api?depois_de={first.id}").get_json()
    assert [m["content"] for m in data["messages"]] == ["Tudo certo?"]
    assert data["chat_open"] is True
    assert navigation_badges(db.session.get(User, owner.id))["messages"] == 0


def test_mensagem_com_html_e_salva_como_texto(client, make_user, make_task, login):
    owner, _, task = chat_setup(make_user, make_task)
    login(owner)
    send(client, task, content="<script>alert(1)</script>")
    html = client.get(f"/mensagens/tarefa/{task.id}").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


# ============================================================== upload

def test_upload_de_imagens_validas_na_criacao(app, client, make_user, login):
    login(make_user(contractor=True))
    response = client.post(
        "/tarefas/nova",
        data=task_form(images=[image(), image("foto.jpg", JPEG_BYTES, "image/jpeg")]),
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    task = Task.query.one()
    assert len(task.images) == 2
    for img in task.images:
        # Nome gerado pelo servidor (UUID), nunca o nome original.
        assert img.filename not in ("foto.png", "foto.jpg")
        assert os.path.isfile(os.path.join(upload_dir(app), img.filename))


def test_upload_recusa_arquivo_falso_e_nao_cria_tarefa(app, client, make_user, login):
    login(make_user(contractor=True))
    client.post(
        "/tarefas/nova",
        data=task_form(images=[image("virus.png", b"MZ isto nao e uma imagem", "image/png")]),
        content_type="multipart/form-data",
    )
    assert Task.query.count() == 0
    assert not os.path.isdir(upload_dir(app)) or os.listdir(upload_dir(app)) == []


def test_upload_recusa_extensao_e_mime_nao_permitidos(client, make_user, login):
    login(make_user(contractor=True))
    client.post("/tarefas/nova", data=task_form(images=[image("anim.gif", b"GIF89a", "image/gif")]),
                content_type="multipart/form-data")
    client.post("/tarefas/nova", data=task_form(images=[image("foto.png", PNG_BYTES, "text/html")]),
                content_type="multipart/form-data")
    assert Task.query.count() == 0


def test_upload_recusa_imagem_grande_e_mais_de_tres(app, client, make_user, login):
    app.config["MAX_IMAGE_SIZE"] = 1024
    login(make_user(contractor=True))
    client.post("/tarefas/nova", data=task_form(images=[image(content=PNG_BYTES + b"\x00" * 2048)]),
                content_type="multipart/form-data")
    client.post("/tarefas/nova", data=task_form(images=[image() for _ in range(4)]),
                content_type="multipart/form-data")
    assert Task.query.count() == 0


def test_edicao_remove_imagem_so_da_propria_tarefa(app, client, make_user, make_task, login):
    owner = make_user(contractor=True)
    other_owner = make_user(contractor=True)
    task = make_task(owner)
    other_task = make_task(other_owner)
    os.makedirs(upload_dir(app), exist_ok=True)
    for name in ("a.png", "b.png"):
        open(os.path.join(upload_dir(app), name), "wb").write(PNG_BYTES)
    mine = TaskImage(task_id=task.id, filename="a.png")
    theirs = TaskImage(task_id=other_task.id, filename="b.png")
    db.session.add_all([mine, theirs])
    db.session.commit()

    login(owner)
    client.post(
        f"/tarefas/{task.id}/editar",
        data=task_form(remove_image=[str(mine.id), str(theirs.id)]),
        content_type="multipart/form-data",
    )
    assert db.session.get(TaskImage, mine.id) is None
    assert not os.path.exists(os.path.join(upload_dir(app), "a.png"))
    assert db.session.get(TaskImage, theirs.id) is not None  # id forjado ignorado
    assert os.path.exists(os.path.join(upload_dir(app), "b.png"))


def test_imagens_aparecem_no_detalhe_card_e_edicao(client, make_user, make_task, login):
    owner = make_user(contractor=True)
    task = make_task(owner, title="Tarefa com foto")
    db.session.add(TaskImage(task_id=task.id, filename="abc123.png"))
    db.session.commit()

    assert "uploads/tasks/abc123.png" in client.get(f"/tarefas/{task.id}").get_data(as_text=True)
    assert "uploads/tasks/abc123.png" in client.get("/tarefas/").get_data(as_text=True)

    login(owner)
    edit_html = client.get(f"/tarefas/{task.id}/editar").get_data(as_text=True)
    assert 'name="remove_image"' in edit_html
    assert 'data-max-files="2"' in edit_html  # 3 - 1 imagem já existente


def test_excluir_tarefa_apaga_imagens_e_salvos(app, client, make_user, make_task, login):
    owner = make_user(contractor=True)
    provider = make_user(provider=True)
    task = make_task(owner)
    os.makedirs(upload_dir(app), exist_ok=True)
    open(os.path.join(upload_dir(app), "c.png"), "wb").write(PNG_BYTES)
    db.session.add_all([
        TaskImage(task_id=task.id, filename="c.png"),
        SavedTask(user_id=provider.id, task_id=task.id),
    ])
    db.session.commit()

    login(owner)
    client.post(f"/tarefas/{task.id}/excluir", data={"csrf_token": CSRF_TOKEN})
    assert TaskImage.query.count() == 0
    assert SavedTask.query.count() == 0
    assert not os.path.exists(os.path.join(upload_dir(app), "c.png"))


# ============================================================== salvar

def test_prestador_salva_e_remove_tarefa(client, make_user, make_task, login):
    task = make_task(make_user(contractor=True))
    login(make_user(provider=True))

    client.post(f"/tarefas/{task.id}/salvar", data={"csrf_token": CSRF_TOKEN})
    assert SavedTask.query.count() == 1
    assert "Tarefas salvas" in client.get("/painel/prestador").get_data(as_text=True)

    client.post(f"/tarefas/{task.id}/salvar", data={"csrf_token": CSRF_TOKEN})
    assert SavedTask.query.count() == 0


def test_salvar_exige_papel_de_prestador_e_tarefa_alheia(client, make_user, make_task, login):
    owner = make_user(contractor=True, provider=True)
    own_task = make_task(owner)
    other_task = make_task(make_user(contractor=True))

    login(owner)
    assert client.post(f"/tarefas/{own_task.id}/salvar", data={"csrf_token": CSRF_TOKEN}).status_code == 403
    logout(client)

    login(make_user(contractor=True))
    assert client.post(f"/tarefas/{other_task.id}/salvar", data={"csrf_token": CSRF_TOKEN}).status_code == 403
    assert SavedTask.query.count() == 0


def test_salvar_nao_redireciona_para_site_externo(client, make_user, make_task, login):
    task = make_task(make_user(contractor=True))
    login(make_user(provider=True))
    response = client.post(
        f"/tarefas/{task.id}/salvar",
        data={"csrf_token": CSRF_TOKEN, "next": "//site-malicioso.com"},
    )
    assert "site-malicioso" not in response.headers["Location"]


# ============================================================== alertas

def test_alerta_conta_tarefas_novas_e_zera_ao_ver_painel(client, make_user, make_task, login):
    provider = make_user(provider=True)
    owner = make_user(contractor=True)
    login(provider)
    client.post("/painel/alertas", data={"category": "Pintura", "city": "Osasco", "csrf_token": CSRF_TOKEN})
    assert Alert.query.count() == 1

    make_task(owner, title="Pintar portão", category="Pintura", city="Osasco")
    make_task(owner, title="Pintura em SP", category="Pintura", city="São Paulo")
    assert navigation_badges(db.session.get(User, provider.id))["alerts"] == 1

    html = client.get("/painel/prestador").get_data(as_text=True)
    assert "Pintar portão" in html and "Pintura em SP" not in html
    assert navigation_badges(db.session.get(User, provider.id))["alerts"] == 0


def test_alerta_exige_categoria_ou_cidade_e_limite(client, make_user, login):
    login(make_user(provider=True))
    client.post("/painel/alertas", data={"category": "", "city": "", "csrf_token": CSRF_TOKEN})
    assert Alert.query.count() == 0

    for city in ["A", "B", "C", "D", "E", "F"]:
        client.post("/painel/alertas", data={"city": city, "csrf_token": CSRF_TOKEN})
    assert Alert.query.count() == Alert.MAX_PER_USER


def test_nao_remove_alerta_de_outra_pessoa(client, make_user, login):
    owner = make_user(provider=True)
    alert = Alert(user_id=owner.id, city="Osasco")
    db.session.add(alert)
    db.session.commit()

    login(make_user(provider=True))
    response = client.post(f"/painel/alertas/{alert.id}/excluir", data={"csrf_token": CSRF_TOKEN})
    assert response.status_code == 403
    assert Alert.query.count() == 1


# ============================================================== painéis

def test_paineis_mostram_proximos_passos(client, make_user, make_task, login):
    owner, provider, task = chat_setup(make_user, make_task)
    db.session.add(Message(task_id=task.id, sender_id=provider.id, content="Cheguei!"))
    db.session.commit()

    login(owner)
    html = client.get("/painel/contratante").get_data(as_text=True)
    assert "Próximos passos" in html and "Combine os detalhes" in html and "Conversar" in html
    logout(client)

    login(provider)
    html = client.get("/painel/prestador").get_data(as_text=True)
    assert "Você foi escolhido(a)" in html
