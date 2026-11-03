# routes/reviews.py
"""Avaliação do prestador pelo contratante, ao final de uma tarefa."""

from flask import Blueprint, abort, flash, redirect, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Review, Task
from utils import validate_csrf_token

reviews_bp = Blueprint("reviews", __name__)

COMMENT_MAX_LENGTH = 500


@reviews_bp.route("/tarefa/<int:task_id>", methods=["POST"])
@login_required
def create(task_id):
    task = db.get_or_404(Task, task_id)
    back_to_task = redirect(url_for("tasks.detail", task_id=task.id))

    # Regras: só o contratante avalia, só depois de concluída, só uma vez.
    if task.contractor_id != current_user.id:
        abort(403)
    if not validate_csrf_token(request.form.get("csrf_token")):
        abort(400)
    if task.status != Task.STATUS_DONE or not task.accepted_provider_id:
        flash("Só é possível avaliar tarefas concluídas.", "error")
        return back_to_task
    if task.review is not None:
        flash("Esta tarefa já foi avaliada.", "info")
        return back_to_task

    rating = request.form.get("rating", type=int)
    comment = request.form.get("comment", "").strip()

    if rating is None or not 1 <= rating <= 5:
        flash("Escolha uma nota de 1 a 5 estrelas.", "error")
        return back_to_task
    if len(comment) > COMMENT_MAX_LENGTH:
        flash(f"O comentário deve ter no máximo {COMMENT_MAX_LENGTH} caracteres.", "error")
        return back_to_task

    review = Review(
        task_id=task.id,
        reviewer_id=current_user.id,
        reviewed_id=task.accepted_provider_id,
        rating=rating,
        comment=comment or None,
    )
    db.session.add(review)
    try:
        db.session.flush()
    except IntegrityError:
        # task_id é UNIQUE em reviews: segunda avaliação simultânea é barrada.
        db.session.rollback()
        flash("Esta tarefa já foi avaliada.", "info")
        return back_to_task

    # Recalcula a média do prestador na mesma transação da avaliação.
    task.accepted_provider.recalculate_rating()
    db.session.commit()

    flash("Obrigado pela avaliação! Ela ajuda outros contratantes a escolher.", "success")
    return back_to_task
