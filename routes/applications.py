# routes/applications.py
"""Candidaturas de prestadores a tarefas: candidatar-se, aceitar, concluir."""

from flask import Blueprint, abort, flash, redirect, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Application, Task
from utils import validate_csrf_token

applications_bp = Blueprint("applications", __name__)


@applications_bp.route("/tarefa/<int:task_id>/candidatar", methods=["POST"])
@login_required
def apply(task_id):
    task = db.get_or_404(Task, task_id)

    if not validate_csrf_token(request.form.get("csrf_token")):
        flash("Sua sessão expirou. Tente novamente.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    if not current_user.is_provider:
        flash("Ative o papel de prestador no seu perfil para se candidatar.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    if task.contractor_id == current_user.id:
        flash("Você não pode se candidatar à sua própria tarefa.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    if task.status != Task.STATUS_OPEN:
        flash("Esta tarefa não está mais aberta para candidaturas.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    # A UniqueConstraint(task_id, provider_id) no banco (Etapa 2) já impede
    # duplicidade em nível de dado; esta checagem aqui só existe para dar
    # uma mensagem amigável em vez de deixar estourar um IntegrityError.
    already_applied = Application.query.filter_by(
        task_id=task.id, provider_id=current_user.id
    ).first()
    if already_applied:
        flash("Você já se candidatou a esta tarefa.", "info")
        return redirect(url_for("tasks.detail", task_id=task.id))

    application = Application(task_id=task.id, provider_id=current_user.id)
    db.session.add(application)
    db.session.commit()

    flash("Candidatura enviada! O contratante vai avaliar seu perfil.", "success")
    return redirect(url_for("tasks.detail", task_id=task.id))


@applications_bp.route("/<int:application_id>/aceitar", methods=["POST"])
@login_required
def accept(application_id):
    application = db.get_or_404(Application, application_id)
    task = application.task

    if task.contractor_id != current_user.id:
        abort(403)
    if not validate_csrf_token(request.form.get("csrf_token")):
        flash("Sua sessão expirou. Tente novamente.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))
    if task.status != Task.STATUS_OPEN:
        flash("Esta tarefa já não está mais aberta.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    # Aceitar um candidato move a tarefa para "em_andamento", trava o
    # prestador escolhido em accepted_provider_id e recusa automaticamente
    # todas as outras candidaturas pendentes — regra de negócio central
    # desta etapa.
    application.status = Application.STATUS_ACCEPTED
    task.status = Task.STATUS_IN_PROGRESS
    task.accepted_provider_id = application.provider_id

    other_applications = Application.query.filter(
        Application.task_id == task.id, Application.id != application.id
    ).all()
    for other in other_applications:
        other.status = Application.STATUS_REJECTED

    db.session.commit()

    flash(f"{application.provider.name} foi aceito para esta tarefa.", "success")
    return redirect(url_for("tasks.detail", task_id=task.id))


@applications_bp.route("/tarefa/<int:task_id>/concluir", methods=["POST"])
@login_required
def complete(task_id):
    task = db.get_or_404(Task, task_id)

    if task.contractor_id != current_user.id:
        abort(403)
    if not validate_csrf_token(request.form.get("csrf_token")):
        flash("Sua sessão expirou. Tente novamente.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))
    if task.status != Task.STATUS_IN_PROGRESS:
        flash("Só é possível concluir uma tarefa que está em andamento.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    task.status = Task.STATUS_DONE
    db.session.commit()

    flash("Tarefa marcada como concluída.", "success")
    return redirect(url_for("tasks.detail", task_id=task.id))
