# services/notifications.py
"""Notificações internas (sem e-mail/push): mensagens não lidas e tarefas
novas que batem com os alertas do prestador.

Tudo é calculado sob demanda a partir do banco — não há fila nem tabela de
notificações, o que é suficiente para o volume de um MVP.
"""

from datetime import datetime

from sqlalchemy import and_, func, or_

from extensions import db
from models import Alert, Application, Message, Task


def unread_messages_query(user):
    """Mensagens recebidas (não enviadas por mim) ainda não lidas, em
    tarefas onde sou contratante ou prestador escolhido."""
    return (
        Message.query.join(Task, Message.task_id == Task.id)
        .filter(
            Message.sender_id != user.id,
            Message.read_at.is_(None),
            or_(Task.contractor_id == user.id, Task.accepted_provider_id == user.id),
        )
    )


def unread_counts_by_task(user):
    """{task_id: quantidade de mensagens não lidas}."""
    rows = (
        unread_messages_query(user)
        .with_entities(Message.task_id, func.count(Message.id))
        .group_by(Message.task_id)
        .all()
    )
    return dict(rows)


def mark_messages_read(task, user):
    """Marca como lidas as mensagens que o outro participante enviou."""
    (
        Message.query.filter(
            Message.task_id == task.id,
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        ).update({Message.read_at: datetime.utcnow()}, synchronize_session=False)
    )


def alert_matches_query(user):
    """Tarefas abertas que batem com algum alerta do prestador.

    Exclui tarefas do próprio usuário e aquelas em que ele já se candidatou
    (não faz sentido alertar sobre o que ele já viu e decidiu).
    """
    alerts = Alert.query.filter_by(user_id=user.id).all()
    if not alerts:
        return None

    conditions = []
    for alert in alerts:
        parts = []
        if alert.category:
            parts.append(Task.category == alert.category)
        if alert.city:
            parts.append(func.lower(Task.city) == alert.city.lower())
        conditions.append(and_(*parts))

    applied_task_ids = db.session.query(Application.task_id).filter(
        Application.provider_id == user.id
    )
    return Task.query.filter(
        Task.status == Task.STATUS_OPEN,
        Task.contractor_id != user.id,
        Task.id.notin_(applied_task_ids),
        or_(*conditions),
    )


def new_alert_matches_count(user):
    query = alert_matches_query(user)
    if query is None:
        return 0
    if user.alerts_seen_at:
        query = query.filter(Task.created_at > user.alerts_seen_at)
    return query.count()


def navigation_badges(user):
    """Contadores exibidos no menu para o usuário logado."""
    badges = {"messages": unread_messages_query(user).count(), "alerts": 0}
    if user.is_provider:
        badges["alerts"] = new_alert_matches_count(user)
    return badges
