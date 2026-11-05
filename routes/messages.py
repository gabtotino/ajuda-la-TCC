# routes/messages.py
"""Chat simples entre contratante e prestador escolhido, por tarefa.

A página carrega o histórico e o static/js/chat.js consulta a API a cada
5 segundos (polling) — sem WebSocket, conforme o escopo do MVP.
Só os dois participantes da tarefa acessam; qualquer outra pessoa recebe 403.
"""

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required

from extensions import db
from models import Message, Task
from services.notifications import mark_messages_read
from utils import validate_csrf_token

messages_bp = Blueprint("messages", __name__)


def _get_chat_task(task_id):
    task = db.get_or_404(Task, task_id)
    if not task.is_chat_participant(current_user):
        abort(403)
    return task


@messages_bp.route("/tarefa/<int:task_id>")
@login_required
def chat(task_id):
    task = _get_chat_task(task_id)
    messages = (
        Message.query.filter_by(task_id=task.id).order_by(Message.id.asc()).all()
    )
    mark_messages_read(task, current_user)
    db.session.commit()

    other = task.accepted_provider if current_user.id == task.contractor_id else task.contractor
    return render_template(
        "messages/chat.html",
        task=task,
        other=other,
        messages=[message.to_dict(current_user.id) for message in messages],
    )


@messages_bp.route("/tarefa/<int:task_id>/api", methods=["GET"])
@login_required
def list_messages(task_id):
    """Mensagens com id maior que ?depois_de= (só as novas, para o polling)."""
    task = _get_chat_task(task_id)
    after_id = request.args.get("depois_de", 0, type=int)
    messages = (
        Message.query.filter(Message.task_id == task.id, Message.id > after_id)
        .order_by(Message.id.asc())
        .limit(100)
        .all()
    )
    mark_messages_read(task, current_user)
    db.session.commit()
    return jsonify(
        messages=[message.to_dict(current_user.id) for message in messages],
        chat_open=task.chat_is_open,
    )


@messages_bp.route("/tarefa/<int:task_id>/api", methods=["POST"])
@login_required
def send_message(task_id):
    task = _get_chat_task(task_id)
    payload = request.get_json(silent=True) or {}

    # Envio via fetch (JSON): o token CSRF vem no corpo, como no assistente de IA.
    if not validate_csrf_token(payload.get("csrf_token")):
        return jsonify(error="Sessão expirada. Recarregue a página."), 400
    if not task.chat_is_open:
        return jsonify(error="A conversa desta tarefa está encerrada."), 403

    content = (payload.get("content") or "").strip()
    if not content:
        return jsonify(error="Escreva uma mensagem."), 400
    if len(content) > Message.MAX_LENGTH:
        return jsonify(error=f"Use no máximo {Message.MAX_LENGTH} caracteres."), 400

    message = Message(task_id=task.id, sender_id=current_user.id, content=content)
    db.session.add(message)
    db.session.commit()
    return jsonify(message=message.to_dict(current_user.id)), 201
