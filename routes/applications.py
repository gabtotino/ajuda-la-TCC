# routes/applications.py
"""Candidaturas de prestadores a tarefas: candidatar-se, aceitar, concluir."""

from flask import Blueprint, abort, flash, redirect, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Application, Task
from utils import parse_money, validate_csrf_token

applications_bp = Blueprint("applications", __name__)

MESSAGE_MIN_LENGTH = 10
MESSAGE_MAX_LENGTH = 500


@applications_bp.route("/tarefa/<int:task_id>/candidatar", methods=["POST"])
@login_required
def apply(task_id):
    task = db.get_or_404(Task, task_id)
    back_to_task = redirect(url_for("tasks.detail", task_id=task.id))

    if not validate_csrf_token(request.form.get("csrf_token")):
        abort(400)

    if not current_user.is_provider:
        flash("Ative o papel de prestador no seu perfil para se candidatar.", "error")
        return back_to_task
    if task.contractor_id == current_user.id:
        abort(403)
    if task.status != Task.STATUS_OPEN:
        flash("Esta tarefa não está mais aberta para candidaturas.", "error")
        return back_to_task

    message = request.form.get("message", "").strip()
    raw_value = request.form.get("proposed_value", "").strip()
    proposed_value = parse_money(raw_value) if raw_value else None

    errors = []
    if not MESSAGE_MIN_LENGTH <= len(message) <= MESSAGE_MAX_LENGTH:
        errors.append(
            f"Escreva uma apresentação entre {MESSAGE_MIN_LENGTH} e {MESSAGE_MAX_LENGTH} caracteres."
        )
    if raw_value and proposed_value is None:
        errors.append("O valor proposto precisa ser um número maior que zero.")
    if errors:
        for error in errors:
            flash(error, "error")
        return back_to_task

    application = Application(
        task_id=task.id,
        provider_id=current_user.id,
        message=message,
        proposed_value=proposed_value,
    )
    db.session.add(application)
    try:
        db.session.commit()
    except IntegrityError:
        # A UniqueConstraint(task_id, provider_id) garante a regra mesmo se
        # dois envios simultâneos passarem pela tela ao mesmo tempo.
        db.session.rollback()
        flash("Você já se candidatou a esta tarefa.", "info")
        return back_to_task

    flash("Candidatura enviada! O contratante vai comparar os candidatos e responder.", "success")
    return back_to_task


@applications_bp.route("/<int:application_id>/aceitar", methods=["POST"])
@login_required
def accept(application_id):
    application = db.get_or_404(Application, application_id)
    task = application.task

    if task.contractor_id != current_user.id:
        abort(403)
    if not validate_csrf_token(request.form.get("csrf_token")):
        abort(400)
    if task.status != Task.STATUS_OPEN or application.status != Application.STATUS_PENDING:
        flash("Esta candidatura não pode mais ser aceita.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    # Aceitar um candidato move a tarefa para "em_andamento", trava o
    # prestador escolhido e recusa automaticamente as demais candidaturas.
    application.status = Application.STATUS_ACCEPTED
    task.status = Task.STATUS_IN_PROGRESS
    task.accepted_provider_id = application.provider_id
    if application.proposed_value:
        # O valor combinado passa a ser o proposto pelo prestador escolhido.
        task.value = application.proposed_value

    for other in task.applications:
        if other.id != application.id:
            other.status = Application.STATUS_REJECTED

    db.session.commit()

    flash(f"{application.provider.name} foi escolhido(a) para esta tarefa.", "success")
    return redirect(url_for("tasks.detail", task_id=task.id))


@applications_bp.route("/tarefa/<int:task_id>/concluir", methods=["POST"])
@login_required
def complete(task_id):
    task = db.get_or_404(Task, task_id)

    if task.contractor_id != current_user.id:
        abort(403)
    if not validate_csrf_token(request.form.get("csrf_token")):
        abort(400)
    if task.status != Task.STATUS_IN_PROGRESS:
        flash("Só é possível concluir uma tarefa que está em andamento.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    task.status = Task.STATUS_DONE
    db.session.commit()

    flash("Tarefa concluída! Que tal avaliar o prestador agora?", "success")
    return redirect(url_for("tasks.detail", task_id=task.id) + "#avaliar")
