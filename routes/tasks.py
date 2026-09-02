# routes/tasks.py
"""CRUD de tarefas: listagem pública, detalhe, criação, edição e exclusão."""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Task
from utils import validate_csrf_token

tasks_bp = Blueprint("tasks", __name__)


def _parse_value(raw_value):
    """Converte o valor digitado (aceita vírgula ou ponto) em Decimal.

    Retorna None se o texto não for um número válido ou não for positivo,
    para que a rota trate isso como erro de validação.
    """
    if not raw_value:
        return None
    raw_value = raw_value.strip()
    # "1.234,56" (formato brasileiro) -> remove separador de milhar e troca
    # a vírgula decimal por ponto. Um valor sem vírgula (ex.: "50.00" ou
    # "50") é interpretado como já está, no formato aceito pelo Decimal.
    if "," in raw_value:
        raw_value = raw_value.replace(".", "").replace(",", ".")
    try:
        value = Decimal(raw_value)
    except InvalidOperation:
        return None
    return value if value > 0 else None


@tasks_bp.route("/")
def list_tasks():
    query = request.args.get("q", "").strip()
    category = request.args.get("categoria", "").strip()

    tasks_query = Task.query
    if query:
        like = f"%{query}%"
        tasks_query = tasks_query.filter(
            db.or_(Task.title.ilike(like), Task.description.ilike(like))
        )
    if category and category in Task.CATEGORIES:
        tasks_query = tasks_query.filter_by(category=category)

    tasks = tasks_query.order_by(Task.created_at.desc()).all()

    return render_template(
        "tasks/list.html",
        tasks=tasks,
        query=query,
        category=category,
        categories=Task.CATEGORIES,
    )


@tasks_bp.route("/<int:task_id>")
def detail(task_id):
    task = db.get_or_404(Task, task_id)
    # Candidatura já enviada por este usuário (se for prestador logado) é
    # usada no template para trocar o botão "Candidatar-se" por um aviso.
    my_application = None
    if current_user.is_authenticated:
        from models import Application

        my_application = Application.query.filter_by(
            task_id=task.id, provider_id=current_user.id
        ).first()
    return render_template("tasks/detail.html", task=task, my_application=my_application)


@tasks_bp.route("/nova", methods=["GET", "POST"])
@login_required
def create():
    if not current_user.is_contractor:
        flash("Só contratantes podem publicar tarefas. Ative esse papel no seu perfil.", "error")
        return redirect(url_for("profile.edit_profile"))

    if request.method == "POST":
        if not validate_csrf_token(request.form.get("csrf_token")):
            flash("Sua sessão expirou. Tente enviar o formulário novamente.", "error")
            return redirect(url_for("tasks.create"))

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        location = request.form.get("location", "").strip()
        value = _parse_value(request.form.get("value", ""))

        errors = []
        if not title:
            errors.append("Informe um título para a tarefa.")
        if not description:
            errors.append("Descreva a tarefa.")
        if category not in Task.CATEGORIES:
            errors.append("Escolha uma categoria válida.")
        if not location:
            errors.append("Informe a localização.")
        if value is None:
            errors.append("Informe um valor numérico maior que zero.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "tasks/create.html",
                categories=Task.CATEGORIES,
                title=title,
                description=description,
                category=category,
                location=location,
                value=request.form.get("value", ""),
            )

        task = Task(
            title=title,
            description=description,
            category=category,
            location=location,
            value=value,
            status=Task.STATUS_OPEN,
            contractor_id=current_user.id,
        )
        db.session.add(task)
        db.session.commit()

        flash("Tarefa publicada com sucesso.", "success")
        return redirect(url_for("tasks.detail", task_id=task.id))

    return render_template("tasks/create.html", categories=Task.CATEGORIES)


@tasks_bp.route("/<int:task_id>/editar", methods=["GET", "POST"])
@login_required
def edit(task_id):
    task = db.get_or_404(Task, task_id)
    if task.contractor_id != current_user.id:
        flash("Você só pode editar tarefas que você publicou.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    if request.method == "POST":
        if not validate_csrf_token(request.form.get("csrf_token")):
            flash("Sua sessão expirou. Tente enviar o formulário novamente.", "error")
            return redirect(url_for("tasks.edit", task_id=task.id))

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        location = request.form.get("location", "").strip()
        value = _parse_value(request.form.get("value", ""))

        errors = []
        if not title:
            errors.append("Informe um título para a tarefa.")
        if not description:
            errors.append("Descreva a tarefa.")
        if category not in Task.CATEGORIES:
            errors.append("Escolha uma categoria válida.")
        if not location:
            errors.append("Informe a localização.")
        if value is None:
            errors.append("Informe um valor numérico maior que zero.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "tasks/edit.html",
                task=task,
                categories=Task.CATEGORIES,
                title=title,
                description=description,
                category=category,
                location=location,
                value=request.form.get("value", ""),
            )

        task.title = title
        task.description = description
        task.category = category
        task.location = location
        task.value = value
        db.session.commit()

        flash("Tarefa atualizada com sucesso.", "success")
        return redirect(url_for("tasks.detail", task_id=task.id))

    return render_template(
        "tasks/edit.html",
        task=task,
        categories=Task.CATEGORIES,
        title=task.title,
        description=task.description,
        category=task.category,
        location=task.location,
        value=str(task.value),
    )


@tasks_bp.route("/<int:task_id>/cancelar", methods=["POST"])
@login_required
def cancel(task_id):
    task = db.get_or_404(Task, task_id)
    if task.contractor_id != current_user.id:
        flash("Você só pode cancelar tarefas que você publicou.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))
    if not validate_csrf_token(request.form.get("csrf_token")):
        flash("Sua sessão expirou. Tente novamente.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    task.status = Task.STATUS_CANCELED
    db.session.commit()
    flash("Tarefa cancelada.", "info")
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/excluir", methods=["POST"])
@login_required
def delete(task_id):
    task = db.get_or_404(Task, task_id)
    if task.contractor_id != current_user.id:
        flash("Você só pode excluir tarefas que você publicou.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))
    if not validate_csrf_token(request.form.get("csrf_token")):
        flash("Sua sessão expirou. Tente novamente.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    db.session.delete(task)
    db.session.commit()
    flash("Tarefa excluída.", "info")
    return redirect(url_for("tasks.list_tasks"))
