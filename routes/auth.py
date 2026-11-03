# routes/auth.py
"""Rotas de autenticação: cadastro, login e logout."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from models import User
from utils import validate_csrf_token

# Um Blueprint agrupa rotas relacionadas (aqui, tudo sobre autenticação) e
# pode ser registrado no app com um prefixo de URL comum — ver app.py, onde
# registramos este blueprint com url_prefix="/auth". Isso mantém as rotas
# organizadas por assunto em vez de todas dentro de um único app.py gigante.
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/cadastro", methods=["GET", "POST"])
def register():
    # Usuário já logado não precisa ver o formulário de cadastro de novo.
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        if not validate_csrf_token(request.form.get("csrf_token")):
            flash("Sua sessão expirou. Tente enviar o formulário novamente.", "error")
            return redirect(url_for("auth.register"))

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role")

        # Validação manual: simples e suficiente para o escopo do MVP,
        # sem precisar de uma biblioteca de formulários (Flask-WTF).
        errors = []
        if not name or len(name) > 120:
            errors.append("Informe seu nome (até 120 caracteres).")
        if not email or "@" not in email or "." not in email.split("@")[-1] or len(email) > 120:
            errors.append("Informe um e-mail válido.")
        if len(password) < 6:
            errors.append("A senha precisa ter pelo menos 6 caracteres.")
        if role not in ("contractor", "provider"):
            errors.append("Escolha se você quer contratar ou prestar serviços.")
        if email and User.query.filter_by(email=email).first() is not None:
            errors.append("Já existe uma conta cadastrada com este e-mail.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("auth/register.html", name=name, email=email)

        user = User(
            name=name,
            email=email,
            is_contractor=(role == "contractor"),
            is_provider=(role == "provider"),
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Já loga o usuário automaticamente após o cadastro, evitando um
        # passo extra de "cadastrou, agora faça login".
        login_user(user)
        flash(f"Bem-vindo(a), {user.name}! Sua conta foi criada.", "success")
        return redirect(url_for("home"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        if not validate_csrf_token(request.form.get("csrf_token")):
            flash("Sua sessão expirou. Tente enviar o formulário novamente.", "error")
            return redirect(url_for("auth.login"))

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        # Mensagem genérica de propósito: não revelamos se o erro foi o
        # e-mail ou a senha, para não ajudar alguém a descobrir quais
        # e-mails estão cadastrados no sistema.
        if user is None or not user.check_password(password):
            flash("E-mail ou senha inválidos.", "error")
            return render_template("auth/login.html", email=email)

        login_user(user)
        flash(f"Bem-vindo(a) de volta, {user.name}!", "success")
        # Volta para a página que pediu login (ex.: candidatar-se), mas só
        # aceita caminhos internos — "next" vindo de fora poderia mandar o
        # usuário para um site malicioso (open redirect).
        next_url = request.args.get("next", "")
        if next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(url_for("home"))

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    # POST + CSRF: com GET, qualquer site poderia deslogar o usuário só
    # embutindo <img src=".../auth/logout"> numa página.
    if not validate_csrf_token(request.form.get("csrf_token")):
        abort(400)
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("home"))
