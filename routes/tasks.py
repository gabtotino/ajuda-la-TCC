# routes/tasks.py
"""CRUD de tarefas: listagem pública com filtros, detalhe, criação, edição,
cancelamento e exclusão."""

from datetime import date

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Application, SavedTask, Task, TaskImage
from services.upload_service import (
    UploadError,
    delete_image_file,
    save_image,
    selected_files,
    validate_image,
)
from services.notifications import unread_counts_by_task
from utils import parse_date, parse_money, safe_next_url, validate_csrf_token

tasks_bp = Blueprint("tasks", __name__)


def _validate_uploads(files, slots_available):
    """Valida as imagens enviadas sem gravar nada ainda.

    Retorna ([(arquivo, extensão), ...], erros). Só depois que TUDO no
    formulário estiver válido os arquivos vão para o disco — assim um erro
    no título não deixa imagens soltas na pasta de uploads.
    """
    errors = []
    if len(files) > slots_available:
        errors.append(
            f"Cada tarefa pode ter no máximo {Task.MAX_IMAGES} imagens "
            f"(você pode adicionar mais {slots_available})."
        )
        return [], errors

    accepted = []
    for file_storage in files:
        try:
            accepted.append((file_storage, validate_image(file_storage)))
        except UploadError as exc:
            errors.append(str(exc))
    return accepted, errors


def _attach_images(task, accepted):
    """Grava os arquivos e cria as linhas TaskImage (antes do commit)."""
    saved = []
    next_position = max((image.position for image in task.images), default=-1) + 1
    for offset, (file_storage, extension) in enumerate(accepted):
        filename = save_image(file_storage, extension)
        saved.append(filename)
        task.images.append(TaskImage(filename=filename, position=next_position + offset))
    return saved

SORT_OPTIONS = {
    "recentes": "Mais recentes",
    "menor_valor": "Menor valor",
    "maior_valor": "Maior valor",
    "data_proxima": "Data mais próxima",
}


def _read_task_form(form):
    """Lê e valida os campos do formulário de tarefa (criar e editar).

    Retorna (dados, erros). Os dados brutos voltam para o template quando
    há erro, para o usuário não perder o que digitou.
    """
    raw = {
        "title": form.get("title", "").strip(),
        "description": form.get("description", "").strip(),
        "requirements": form.get("requirements", "").strip(),
        "category": form.get("category", "").strip(),
        "city": form.get("city", "").strip(),
        "neighborhood": form.get("neighborhood", "").strip(),
        "desired_date": form.get("desired_date", "").strip(),
        "time_period": form.get("time_period", "qualquer").strip(),
        "is_flexible": form.get("is_flexible") == "on",
        "value": form.get("value", "").strip(),
    }

    errors = []
    if not raw["title"] or len(raw["title"]) > 150:
        errors.append("Informe um título de até 150 caracteres.")
    if len(raw["description"]) < 10:
        errors.append("Descreva a tarefa com pelo menos 10 caracteres.")
    if len(raw["requirements"]) > 1000:
        errors.append("Os requisitos devem ter no máximo 1000 caracteres.")
    if raw["category"] not in Task.CATEGORIES:
        errors.append("Escolha uma categoria válida.")
    if not raw["city"] or len(raw["city"]) > 80:
        errors.append("Informe a cidade.")
    if not raw["neighborhood"] or len(raw["neighborhood"]) > 80:
        errors.append("Informe o bairro.")
    if raw["time_period"] not in Task.TIME_PERIODS:
        errors.append("Escolha um período válido.")

    desired_date = parse_date(raw["desired_date"])
    if desired_date is None:
        errors.append("Informe a data desejada.")
    elif desired_date < date.today():
        errors.append("A data desejada não pode estar no passado.")

    value = parse_money(raw["value"])
    if value is None:
        errors.append("Informe um valor maior que zero (ex.: 80,00).")

    clean = dict(raw, desired_date=desired_date, value=value, requirements=raw["requirements"] or None)
    return raw, clean, errors


def _get_owned_task(task_id):
    """Busca a tarefa e garante que o usuário logado é o contratante."""
    task = db.get_or_404(Task, task_id)
    if task.contractor_id != current_user.id:
        abort(403)
    return task


@tasks_bp.route("/")
def list_tasks():
    args = request.args
    filters = {
        "q": args.get("q", "").strip(),
        "categoria": args.get("categoria", "").strip(),
        "cidade": args.get("cidade", "").strip(),
        "bairro": args.get("bairro", "").strip(),
        "valor_min": args.get("valor_min", "").strip(),
        "valor_max": args.get("valor_max", "").strip(),
        "data": args.get("data", "").strip(),
    }
    sort = args.get("ordem", "recentes")
    if sort not in SORT_OPTIONS:
        sort = "recentes"

    # A listagem pública só mostra tarefas abertas: tarefas encerradas
    # ficam visíveis apenas para os envolvidos (no detalhe e nos painéis).
    query = Task.query.filter(Task.status == Task.STATUS_OPEN)

    if filters["q"]:
        like = f"%{filters['q']}%"
        query = query.filter(db.or_(Task.title.ilike(like), Task.description.ilike(like)))
    if filters["categoria"] in Task.CATEGORIES:
        query = query.filter(Task.category == filters["categoria"])
    if filters["cidade"]:
        query = query.filter(Task.city.ilike(filters["cidade"]))
    if filters["bairro"]:
        query = query.filter(Task.neighborhood.ilike(f"%{filters['bairro']}%"))

    min_value = parse_money(filters["valor_min"])
    max_value = parse_money(filters["valor_max"])
    if min_value is not None:
        query = query.filter(Task.value >= min_value)
    if max_value is not None:
        query = query.filter(Task.value <= max_value)

    from_date = parse_date(filters["data"])
    if from_date:
        query = query.filter(Task.desired_date >= from_date)

    if sort == "menor_valor":
        query = query.order_by(Task.value.asc(), Task.created_at.desc())
    elif sort == "maior_valor":
        query = query.order_by(Task.value.desc(), Task.created_at.desc())
    elif sort == "data_proxima":
        # Tarefas sem data vão para o fim da lista.
        query = query.order_by(Task.desired_date.is_(None), Task.desired_date.asc())
    else:
        query = query.order_by(Task.created_at.desc())

    page = args.get("page", 1, type=int)
    pagination = query.paginate(
        page=max(page, 1), per_page=current_app.config["TASKS_PER_PAGE"], error_out=False
    )

    cities = [
        row[0]
        for row in db.session.query(Task.city)
        .filter(Task.status == Task.STATUS_OPEN, Task.city != "")
        .distinct()
        .order_by(Task.city)
        .all()
    ]

    # Só os filtros preenchidos entram nos links de paginação.
    active_filters = {key: value for key, value in filters.items() if value}
    if sort != "recentes":
        active_filters["ordem"] = sort

    return render_template(
        "tasks/list.html",
        pagination=pagination,
        tasks=pagination.items,
        filters=filters,
        active_filters=active_filters,
        sort=sort,
        sort_options=SORT_OPTIONS,
        categories=Task.CATEGORIES,
        cities=cities,
    )


@tasks_bp.route("/<int:task_id>")
def detail(task_id):
    task = db.get_or_404(Task, task_id)

    # Tarefa encerrada só aparece para quem está envolvido nela. Para os
    # demais respondemos 404 (e não 403) para não revelar que ela existe.
    if not task.can_be_viewed_by(current_user):
        abort(404)

    my_application = None
    if current_user.is_authenticated:
        my_application = Application.query.filter_by(
            task_id=task.id, provider_id=current_user.id
        ).first()

    is_owner = current_user.is_authenticated and task.contractor_id == current_user.id
    can_apply = (
        current_user.is_authenticated
        and current_user.is_provider
        and not is_owner
        and task.status == Task.STATUS_OPEN
        and my_application is None
    )
    contractor_task_count = Task.query.filter_by(contractor_id=task.contractor_id).count()

    is_chat_participant = task.is_chat_participant(current_user)
    chat_unread = (
        unread_counts_by_task(current_user).get(task.id, 0) if is_chat_participant else 0
    )

    return render_template(
        "tasks/detail.html",
        task=task,
        is_owner=is_owner,
        my_application=my_application,
        can_apply=can_apply,
        contractor_task_count=contractor_task_count,
        is_chat_participant=is_chat_participant,
        chat_unread=chat_unread,
    )


@tasks_bp.route("/nova", methods=["GET", "POST"])
@login_required
def create():
    if not current_user.is_contractor:
        flash("Só contratantes podem publicar tarefas. Ative esse papel no seu perfil.", "error")
        return redirect(url_for("profile.edit_profile"))

    context = {"categories": Task.CATEGORIES, "time_periods": Task.TIME_PERIODS, "today": date.today()}

    if request.method == "POST":
        if not validate_csrf_token(request.form.get("csrf_token")):
            flash("Sua sessão expirou. Tente enviar o formulário novamente.", "error")
            return redirect(url_for("tasks.create"))

        raw, clean, errors = _read_task_form(request.form)
        files = selected_files(request.files)
        accepted, upload_errors = _validate_uploads(files, Task.MAX_IMAGES)
        errors += upload_errors
        if errors:
            for error in errors:
                flash(error, "error")
            if files:
                # O navegador não guarda arquivos entre envios por segurança.
                flash("Selecione as imagens novamente antes de publicar.", "info")
            return render_template("tasks/create.html", form=raw, **context)

        task = Task(
            title=clean["title"],
            description=clean["description"],
            requirements=clean["requirements"],
            category=clean["category"],
            city=clean["city"],
            neighborhood=clean["neighborhood"],
            desired_date=clean["desired_date"],
            time_period=clean["time_period"],
            is_flexible=clean["is_flexible"],
            value=clean["value"],
            status=Task.STATUS_OPEN,
            contractor_id=current_user.id,
        )
        db.session.add(task)
        saved_files = _attach_images(task, accepted)
        try:
            db.session.commit()
        except Exception:
            # Se o banco falhar, os arquivos já gravados não podem ficar
            # órfãos na pasta de uploads.
            db.session.rollback()
            for filename in saved_files:
                delete_image_file(filename)
            raise

        flash("Tarefa publicada! Agora é só aguardar as candidaturas.", "success")
        return redirect(url_for("tasks.detail", task_id=task.id))

    # Pré-preenche a cidade com a do perfil para agilizar o cadastro.
    return render_template("tasks/create.html", form={"city": current_user.city or ""}, **context)


@tasks_bp.route("/<int:task_id>/editar", methods=["GET", "POST"])
@login_required
def edit(task_id):
    task = _get_owned_task(task_id)
    if task.status != Task.STATUS_OPEN:
        flash("Só é possível editar tarefas que ainda estão abertas.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    context = {"task": task, "categories": Task.CATEGORIES, "time_periods": Task.TIME_PERIODS, "today": date.today()}

    if request.method == "POST":
        if not validate_csrf_token(request.form.get("csrf_token")):
            flash("Sua sessão expirou. Tente enviar o formulário novamente.", "error")
            return redirect(url_for("tasks.edit", task_id=task.id))

        raw, clean, errors = _read_task_form(request.form)

        # Imagens marcadas para remoção: só ids que pertencem a ESTA tarefa
        # contam (um id de outra tarefa, forjado no formulário, é ignorado).
        remove_ids = set(request.form.getlist("remove_image", type=int))
        to_remove = [image for image in task.images if image.id in remove_ids]
        slots = Task.MAX_IMAGES - (len(task.images) - len(to_remove))
        accepted, upload_errors = _validate_uploads(selected_files(request.files), slots)
        errors += upload_errors

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("tasks/edit.html", form=raw, **context)

        for field in (
            "title", "description", "requirements", "category", "city",
            "neighborhood", "desired_date", "time_period", "is_flexible", "value",
        ):
            setattr(task, field, clean[field])

        removed_files = [image.filename for image in to_remove]
        for image in to_remove:
            task.images.remove(image)  # delete-orphan apaga a linha no commit
        saved_files = _attach_images(task, accepted)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            for filename in saved_files:
                delete_image_file(filename)
            raise

        for filename in removed_files:
            delete_image_file(filename)

        flash("Tarefa atualizada com sucesso.", "success")
        return redirect(url_for("tasks.detail", task_id=task.id))

    form = {
        "title": task.title,
        "description": task.description,
        "requirements": task.requirements or "",
        "category": task.category,
        "city": task.city,
        "neighborhood": task.neighborhood,
        "desired_date": task.desired_date.isoformat() if task.desired_date else "",
        "time_period": task.time_period,
        "is_flexible": task.is_flexible,
        "value": str(task.value).replace(".", ","),
    }
    return render_template("tasks/edit.html", form=form, **context)


@tasks_bp.route("/<int:task_id>/cancelar", methods=["POST"])
@login_required
def cancel(task_id):
    task = _get_owned_task(task_id)
    if not validate_csrf_token(request.form.get("csrf_token")):
        abort(400)
    if task.status != Task.STATUS_OPEN:
        flash("Só é possível cancelar tarefas abertas.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    task.status = Task.STATUS_CANCELED
    # Candidaturas pendentes de uma tarefa cancelada não têm mais chance de
    # serem aceitas; marcá-las como recusadas mantém o painel do prestador
    # coerente.
    for application in task.applications:
        if application.status == Application.STATUS_PENDING:
            application.status = Application.STATUS_REJECTED
    db.session.commit()
    flash("Tarefa cancelada.", "info")
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/excluir", methods=["POST"])
@login_required
def delete(task_id):
    task = _get_owned_task(task_id)
    if not validate_csrf_token(request.form.get("csrf_token")):
        abort(400)
    # Tarefas com prestador envolvido (em andamento/concluídas) guardam
    # histórico e avaliação; só tarefas abertas ou canceladas podem sumir.
    if task.status not in (Task.STATUS_OPEN, Task.STATUS_CANCELED):
        flash("Tarefas em andamento ou concluídas não podem ser excluídas.", "error")
        return redirect(url_for("tasks.detail", task_id=task.id))

    image_files = [image.filename for image in task.images]

    # O cascade definido em Task remove candidaturas, mensagens, avaliação,
    # imagens e os registros de "tarefa salva" que apontam para ela.
    db.session.delete(task)
    db.session.commit()

    # Arquivos só são apagados depois do commit: se o banco falhasse, não
    # queremos ter perdido as imagens de uma tarefa que continua existindo.
    for filename in image_files:
        delete_image_file(filename)
    flash("Tarefa excluída.", "info")
    return redirect(url_for("dashboard.home"))


@tasks_bp.route("/<int:task_id>/salvar", methods=["POST"])
@login_required
def toggle_saved(task_id):
    """Salva (ou remove dos salvos) uma tarefa, para prestadores."""
    task = db.get_or_404(Task, task_id)
    if not validate_csrf_token(request.form.get("csrf_token")):
        abort(400)
    if not current_user.is_provider or task.contractor_id == current_user.id:
        abort(403)

    saved = SavedTask.query.filter_by(user_id=current_user.id, task_id=task.id).first()
    if saved:
        db.session.delete(saved)
        flash("Tarefa removida dos salvos.", "info")
    elif task.status != Task.STATUS_OPEN:
        flash("Só é possível salvar tarefas abertas.", "error")
    else:
        db.session.add(SavedTask(user_id=current_user.id, task_id=task.id))
        flash("Tarefa salva! Ela fica no seu painel para decidir depois.", "success")
    db.session.commit()

    return redirect(safe_next_url(request.form.get("next")) or url_for("tasks.detail", task_id=task.id))
