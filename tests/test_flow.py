# tests/test_flow.py
"""Fluxo principal: candidatura -> aceite -> conclusão -> avaliação."""

from extensions import db
from models import Application, Review, Task, User
from tests.conftest import CSRF_TOKEN


def apply(client, task, message="Tenho experiência e consigo ir no horário.", value=""):
    return client.post(
        f"/candidaturas/tarefa/{task.id}/candidatar",
        data={"message": message, "proposed_value": value, "csrf_token": CSRF_TOKEN},
    )


def logout(client):
    client.post("/auth/logout", data={"csrf_token": CSRF_TOKEN})


# ---------------------------------------------------------------- candidatura

def test_candidatura_exige_mensagem(client, make_user, make_task, login):
    task = make_task(make_user(contractor=True))
    login(make_user(provider=True))
    apply(client, task, message="oi")
    assert Application.query.count() == 0


def test_candidatura_com_mensagem_e_valor_proposto(client, make_user, make_task, login):
    task = make_task(make_user(contractor=True))
    login(make_user(provider=True))
    apply(client, task, value="45,00")

    application = Application.query.one()
    assert application.message.startswith("Tenho experiência")
    assert str(application.proposed_value) == "45.00"
    assert application.status == Application.STATUS_PENDING


def test_candidatura_duplicada_e_bloqueada(client, make_user, make_task, login):
    task = make_task(make_user(contractor=True))
    login(make_user(provider=True))
    apply(client, task)
    apply(client, task)
    assert Application.query.count() == 1


def test_contratante_nao_se_candidata_a_propria_tarefa(client, make_user, make_task, login):
    owner = make_user(contractor=True, provider=True)
    task = make_task(owner)
    login(owner)
    assert apply(client, task).status_code == 403
    assert Application.query.count() == 0


def test_usuario_sem_papel_de_prestador_nao_se_candidata(client, make_user, make_task, login):
    task = make_task(make_user(contractor=True))
    login(make_user(contractor=True))
    apply(client, task)
    assert Application.query.count() == 0


def test_nao_candidata_em_tarefa_encerrada(client, make_user, make_task, login):
    task = make_task(make_user(contractor=True), status=Task.STATUS_CANCELED)
    login(make_user(provider=True))
    apply(client, task)
    assert Application.query.count() == 0


# ---------------------------------------------------------------- aceite

def test_aceite_move_tarefa_e_recusa_demais(client, make_user, make_task, login):
    owner = make_user(contractor=True)
    task = make_task(owner, value=60)
    chosen = make_user(provider=True)
    other = make_user(provider=True)
    db.session.add_all([
        Application(task_id=task.id, provider_id=chosen.id, message="Escolha-me, por favor!", proposed_value=55),
        Application(task_id=task.id, provider_id=other.id, message="Também posso ajudar!"),
    ])
    db.session.commit()
    chosen_application = Application.query.filter_by(provider_id=chosen.id).one()

    login(owner)
    client.post(f"/candidaturas/{chosen_application.id}/aceitar", data={"csrf_token": CSRF_TOKEN})

    task = db.session.get(Task, task.id)
    assert task.status == Task.STATUS_IN_PROGRESS
    assert task.accepted_provider_id == chosen.id
    assert str(task.value) == "55.00"  # valor proposto pelo escolhido vira o combinado
    assert Application.query.filter_by(provider_id=other.id).one().status == Application.STATUS_REJECTED


def test_so_o_contratante_aceita(client, make_user, make_task, login):
    task = make_task(make_user(contractor=True))
    provider = make_user(provider=True)
    application = Application(task_id=task.id, provider_id=provider.id, message="Posso ajudar sim!")
    db.session.add(application)
    db.session.commit()

    login(provider)
    response = client.post(f"/candidaturas/{application.id}/aceitar", data={"csrf_token": CSRF_TOKEN})
    assert response.status_code == 403
    assert db.session.get(Task, task.id).status == Task.STATUS_OPEN


# ---------------------------------------------------------------- conclusão

def test_conclusao_so_de_tarefa_em_andamento_e_pelo_contratante(client, make_user, make_task, login):
    owner = make_user(contractor=True)
    provider = make_user(provider=True)
    open_task = make_task(owner)
    running = make_task(owner, status=Task.STATUS_IN_PROGRESS, accepted_provider_id=provider.id)

    login(provider)
    assert client.post(f"/candidaturas/tarefa/{running.id}/concluir", data={"csrf_token": CSRF_TOKEN}).status_code == 403
    logout(client)

    login(owner)
    client.post(f"/candidaturas/tarefa/{open_task.id}/concluir", data={"csrf_token": CSRF_TOKEN})
    client.post(f"/candidaturas/tarefa/{running.id}/concluir", data={"csrf_token": CSRF_TOKEN})
    assert db.session.get(Task, open_task.id).status == Task.STATUS_OPEN
    assert db.session.get(Task, running.id).status == Task.STATUS_DONE


# ---------------------------------------------------------------- avaliação

def review(client, task, rating=5, comment="Excelente!"):
    return client.post(
        f"/avaliacoes/tarefa/{task.id}",
        data={"rating": rating, "comment": comment, "csrf_token": CSRF_TOKEN},
    )


def test_avaliacao_recalcula_media_do_prestador(client, make_user, make_task, login):
    owner = make_user(contractor=True)
    provider = make_user(provider=True)
    first = make_task(owner, status=Task.STATUS_DONE, accepted_provider_id=provider.id)
    second = make_task(owner, status=Task.STATUS_DONE, accepted_provider_id=provider.id)

    login(owner)
    review(client, first, rating=5)
    review(client, second, rating=4)

    assert Review.query.count() == 2
    assert db.session.get(User, provider.id).avg_rating == 4.5

    profile_html = client.get(f"/perfil/{provider.id}").get_data(as_text=True)
    assert "Excelente!" in profile_html
    assert "4.5" in profile_html


def test_avaliacao_unica_por_tarefa(client, make_user, make_task, login):
    owner = make_user(contractor=True)
    provider = make_user(provider=True)
    task = make_task(owner, status=Task.STATUS_DONE, accepted_provider_id=provider.id)

    login(owner)
    review(client, task, rating=5)
    review(client, task, rating=1)
    assert Review.query.count() == 1
    assert db.session.get(User, provider.id).avg_rating == 5.0


def test_avaliacao_so_do_contratante_e_de_tarefa_concluida(client, make_user, make_task, login):
    owner = make_user(contractor=True)
    provider = make_user(provider=True)
    running = make_task(owner, status=Task.STATUS_IN_PROGRESS, accepted_provider_id=provider.id)
    done = make_task(owner, status=Task.STATUS_DONE, accepted_provider_id=provider.id)

    login(provider)
    assert review(client, done).status_code == 403
    logout(client)

    login(owner)
    review(client, running)
    assert Review.query.count() == 0


def test_avaliacao_rejeita_nota_fora_do_intervalo(client, make_user, make_task, login):
    owner = make_user(contractor=True)
    provider = make_user(provider=True)
    task = make_task(owner, status=Task.STATUS_DONE, accepted_provider_id=provider.id)

    login(owner)
    review(client, task, rating=6)
    review(client, task, rating=0)
    assert Review.query.count() == 0


def test_fluxo_completo_pela_interface(client, make_user, make_task, login):
    owner = make_user(contractor=True, name="Contratante")
    provider = make_user(provider=True, name="Prestadora")
    task = make_task(owner)

    login(provider)
    apply(client, task)
    logout(client)

    login(owner)
    detail = client.get(f"/tarefas/{task.id}").get_data(as_text=True)
    assert "Prestadora" in detail and "Tenho experiência" in detail  # comparação de candidatos

    application = Application.query.one()
    client.post(f"/candidaturas/{application.id}/aceitar", data={"csrf_token": CSRF_TOKEN})
    client.post(f"/candidaturas/tarefa/{task.id}/concluir", data={"csrf_token": CSRF_TOKEN})
    review(client, task, rating=5)

    assert db.session.get(Task, task.id).status == Task.STATUS_DONE
    assert db.session.get(User, provider.id).avg_rating == 5.0
