# routes/dashboard.py
"""Painéis de contratante e prestador, com dados reais do usuário logado."""

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from models import Application, Task

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def home():
    # Manda para o painel do papel principal do usuário; quem tem os dois
    # papéis pode trocar de aba dentro da própria página do painel.
    if current_user.is_contractor:
        return redirect(url_for("dashboard.contractor"))
    if current_user.is_provider:
        return redirect(url_for("dashboard.provider"))
    flash("Seu perfil não tem nenhum papel ativo. Edite seu perfil primeiro.", "error")
    return redirect(url_for("profile.edit_profile"))


@dashboard_bp.route("/contratante")
@login_required
def contractor():
    if not current_user.is_contractor:
        flash("Você precisa ativar o papel de contratante no seu perfil.", "error")
        return redirect(url_for("profile.edit_profile"))

    tasks = Task.query.filter_by(contractor_id=current_user.id).order_by(
        Task.created_at.desc()
    ).all()

    # Agrupa em Python (em vez de 4 queries separadas) já que o volume de
    # tarefas por contratante é pequeno neste MVP.
    tasks_by_status = {status: [] for status in Task.STATUSES}
    for task in tasks:
        tasks_by_status[task.status].append(task)

    pending_applications = (
        Application.query.join(Task)
        .filter(Task.contractor_id == current_user.id, Application.status == Application.STATUS_PENDING)
        .all()
    )

    stats = {
        "total": len(tasks),
        "abertas": len(tasks_by_status[Task.STATUS_OPEN]),
        "em_andamento": len(tasks_by_status[Task.STATUS_IN_PROGRESS]),
        "concluidas": len(tasks_by_status[Task.STATUS_DONE]),
        "candidatos_pendentes": len(pending_applications),
    }

    return render_template(
        "dashboard/contractor.html",
        tasks_by_status=tasks_by_status,
        pending_applications=pending_applications,
        stats=stats,
        show_provider_tab=current_user.is_provider,
    )


@dashboard_bp.route("/prestador")
@login_required
def provider():
    if not current_user.is_provider:
        flash("Você precisa ativar o papel de prestador no seu perfil.", "error")
        return redirect(url_for("profile.edit_profile"))

    applications = (
        Application.query.filter_by(provider_id=current_user.id)
        .order_by(Application.created_at.desc())
        .all()
    )

    stats = {
        "enviadas": len(applications),
        "aceitas": len([a for a in applications if a.status == Application.STATUS_ACCEPTED]),
        "concluidas": len(
            [a for a in applications if a.status == Application.STATUS_ACCEPTED and a.task.status == Task.STATUS_DONE]
        ),
        "avaliacao_media": current_user.avg_rating,
    }

    return render_template(
        "dashboard/provider.html",
        applications=applications,
        stats=stats,
        show_contractor_tab=current_user.is_contractor,
    )
