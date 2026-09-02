# routes/profile.py
"""Rotas de perfil: visualização (própria ou de outro usuário) e edição."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import User
from utils import validate_csrf_token

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/")
@login_required
def my_profile():
    # Atalho: "/perfil" sempre redireciona para o perfil de quem está logado.
    return redirect(url_for("profile.view_profile", user_id=current_user.id))


@profile_bp.route("/<int:user_id>")
@login_required
def view_profile(user_id):
    # Perfil é visível para qualquer usuário logado (útil mais adiante para
    # o contratante avaliar um candidato antes de aceitar, Etapa 7).
    user = db.get_or_404(User, user_id)
    return render_template("profile/view.html", profile_user=user)


@profile_bp.route("/editar", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        if not validate_csrf_token(request.form.get("csrf_token")):
            flash("Sua sessão expirou. Tente enviar o formulário novamente.", "error")
            return redirect(url_for("profile.edit_profile"))

        name = request.form.get("name", "").strip()
        bio = request.form.get("bio", "").strip()
        city = request.form.get("city", "").strip()
        # Checkbox desmarcado simplesmente não vem no request.form, por isso
        # comparamos com "on" em vez de usar request.form.get(...) direto.
        is_contractor = request.form.get("is_contractor") == "on"
        is_provider = request.form.get("is_provider") == "on"

        errors = []
        if not name:
            errors.append("Informe seu nome.")
        if not (is_contractor or is_provider):
            errors.append("Selecione pelo menos um papel: contratante ou prestador.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "profile/edit.html",
                name=name,
                bio=bio,
                city=city,
                is_contractor=is_contractor,
                is_provider=is_provider,
            )

        current_user.name = name
        current_user.bio = bio or None
        current_user.city = city or None
        current_user.is_contractor = is_contractor
        current_user.is_provider = is_provider
        db.session.commit()

        flash("Perfil atualizado com sucesso.", "success")
        return redirect(url_for("profile.view_profile", user_id=current_user.id))

    return render_template(
        "profile/edit.html",
        name=current_user.name,
        bio=current_user.bio or "",
        city=current_user.city or "",
        is_contractor=current_user.is_contractor,
        is_provider=current_user.is_provider,
    )
