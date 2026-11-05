# routes/dashboard.py
"""Painéis de contratante e prestador: próximos passos, tarefas ativas,
tarefas salvas, alertas e histórico, com dados reais do usuário logado."""

from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Alert, Application, SavedTask, Task
from services.notifications import alert_matches_query, unread_counts_by_task
from utils import validate_csrf_token

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

    unread = unread_counts_by_task(current_user)

    # Próximos passos, em ordem de urgência: escolher candidatos, combinar
    # com quem foi escolhido e avaliar quem já concluiu.
    to_choose = [
        (task, sum(1 for a in task.applications if a.status == Application.STATUS_PENDING))
        for task in tasks_by_status[Task.STATUS_OPEN]
    ]
    to_choose = [(task, count) for task, count in to_choose if count]
    in_progress = tasks_by_status[Task.STATUS_IN_PROGRESS]
    pending_reviews = [task for task in tasks_by_status[Task.STATUS_DONE] if task.review is None]

    stats = {
        "abertas": len(tasks_by_status[Task.STATUS_OPEN]),
        "em_andamento": len(in_progress),
        "concluidas": len(tasks_by_status[Task.STATUS_DONE]),
        "candidatos_pendentes": sum(count for _, count in to_choose),
    }

    return render_template(
        "dashboard/contractor.html",
        to_choose=to_choose,
        in_progress=in_progress,
        pending_reviews=pending_reviews,
        open_tasks=tasks_by_status[Task.STATUS_OPEN],
        history=tasks_by_status[Task.STATUS_DONE] + tasks_by_status[Task.STATUS_CANCELED],
        unread=unread,
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
    pending = [a for a in applications if a.status == Application.STATUS_PENDING]
    rejected = [a for a in applications if a.status == Application.STATUS_REJECTED]

    # Quem foi escolhido é definido por Task.accepted_provider_id (fonte da
    # verdade do aceite), não pela lista de candidaturas.
    chosen = (
        Task.query.filter_by(accepted_provider_id=current_user.id)
        .order_by(Task.created_at.desc())
        .all()
    )
    active = [task for task in chosen if task.status == Task.STATUS_IN_PROGRESS]
    done = [task for task in chosen if task.status == Task.STATUS_DONE]

    saved = (
        SavedTask.query.filter_by(user_id=current_user.id)
        .order_by(SavedTask.created_at.desc())
        .all()
    )

    alerts = Alert.query.filter_by(user_id=current_user.id).order_by(Alert.created_at).all()
    matches_query = alert_matches_query(current_user)
    alert_matches = matches_query.order_by(Task.created_at.desc()).limit(8).all() if matches_query else []

    # Marca o que é novidade desde a última visita e registra esta visita:
    # o contador do menu zera depois que o prestador viu as tarefas.
    seen_at = current_user.alerts_seen_at
    new_match_ids = {task.id for task in alert_matches if seen_at is None or task.created_at > seen_at}
    current_user.alerts_seen_at = datetime.utcnow()
    db.session.commit()

    stats = {
        "pendentes": len(pending),
        "em_andamento": len(active),
        "concluidas": len(done),
        "avaliacao_media": current_user.avg_rating if current_user.review_count else None,
    }

    return render_template(
        "dashboard/provider.html",
        pending=pending,
        active=active,
        done=done,
        rejected=rejected,
        saved=saved,
        alerts=alerts,
        alert_matches=alert_matches,
        new_match_ids=new_match_ids,
        unread=unread_counts_by_task(current_user),
        categories=Task.CATEGORIES,
        max_alerts=Alert.MAX_PER_USER,
        stats=stats,
        show_contractor_tab=current_user.is_contractor,
    )


@dashboard_bp.route("/alertas", methods=["POST"])
@login_required
def create_alert():
    if not validate_csrf_token(request.form.get("csrf_token")):
        abort(400)
    if not current_user.is_provider:
        abort(403)

    category = request.form.get("category", "").strip() or None
    city = request.form.get("city", "").strip() or None
    back = redirect(url_for("dashboard.provider") + "#alertas")

    if category and category not in Task.CATEGORIES:
        flash("Escolha uma categoria válida.", "error")
        return back
    if city and len(city) > 80:
        flash("A cidade deve ter no máximo 80 caracteres.", "error")
        return back
    if not category and not city:
        flash("Escolha uma categoria, uma cidade ou as duas.", "error")
        return back
    if Alert.query.filter_by(user_id=current_user.id).count() >= Alert.MAX_PER_USER:
        flash(f"Você pode ter no máximo {Alert.MAX_PER_USER} alertas. Remova um para criar outro.", "error")
        return back

    duplicate = Alert.query.filter(
        Alert.user_id == current_user.id,
        Alert.category.is_(category) if category is None else Alert.category == category,
        Alert.city.is_(city) if city is None else db.func.lower(Alert.city) == city.lower(),
    ).first()
    if duplicate:
        flash("Você já tem um alerta igual a esse.", "info")
        return back

    db.session.add(Alert(user_id=current_user.id, category=category, city=city))
    db.session.commit()
    flash("Alerta criado! Tarefas compatíveis aparecem aqui e no menu.", "success")
    return back


@dashboard_bp.route("/alertas/<int:alert_id>/excluir", methods=["POST"])
@login_required
def delete_alert(alert_id):
    if not validate_csrf_token(request.form.get("csrf_token")):
        abort(400)
    alert = db.get_or_404(Alert, alert_id)
    if alert.user_id != current_user.id:
        abort(403)
    db.session.delete(alert)
    db.session.commit()
    flash("Alerta removido.", "info")
    return redirect(url_for("dashboard.provider") + "#alertas")
