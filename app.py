# app.py
"""Ponto de entrada da aplicação Ajuda-Lá."""

import os

from flask import Flask, render_template

from config import Config
from extensions import db, login_manager, migrate

# Textos das páginas de erro, num único lugar: todas usam o mesmo template
# (errors/error.html) e só mudam código, título e mensagem.
ERROR_PAGES = {
    403: ("Acesso negado", "Você não tem permissão para acessar esta página ou executar esta ação."),
    404: ("Página não encontrada", "O link que você seguiu pode estar quebrado, ou a página não está mais disponível."),
    413: ("Arquivo grande demais", "O envio ultrapassou o limite de 5 MB. Tente novamente com um arquivo menor."),
    500: ("Algo deu errado do nosso lado", "Tente novamente em alguns instantes."),
}


def _static_version(static_folder):
    mtimes = [
        os.path.getmtime(os.path.join(root, name))
        for sub in ("css", "js")
        for root, _, files in os.walk(os.path.join(static_folder, sub))
        for name in files
    ]
    return str(int(max(mtimes))) if mtimes else "1"


def create_app(config_class=Config):
    """Application factory: monta e configura a instância do Flask.

    Usamos uma factory (em vez de criar `app = Flask(__name__)` direto no
    módulo, como na Etapa 1) por dois motivos: evita import circular quando
    models e rotas também precisam importar `db` a partir deste arquivo, e
    permite criar múltiplas instâncias da aplicação — os testes passam
    TestConfig para usar um banco em memória isolado.

    O comando `flask` encontra esta função automaticamente (ele procura por
    `create_app` em app.py), então não precisamos de uma instância global.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY não definida. Configure-a no arquivo .env (veja .env.example)."
        )

    # Liga as extensões (SQLAlchemy, Migrate) a esta instância específica
    # do app. Elas foram criadas "vazias" em extensions.py justamente para
    # serem inicializadas aqui. render_as_batch permite que migrations
    # autogeradas alterem colunas no SQLite (que não tem ALTER TABLE completo).
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    login_manager.init_app(app)

    # Rota para onde o Flask-Login redireciona quando um usuário anônimo
    # tenta acessar uma página marcada com @login_required.
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para continuar."
    login_manager.login_message_category = "info"

    # Importa os models dentro da factory para registrá-los no metadata do
    # SQLAlchemy (é o que "flask db migrate" inspeciona).
    from models import Application, Message, Review, Task, User  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        # Flask-Login chama esta função em toda request autenticada para
        # recarregar o User a partir do id guardado na sessão.
        return db.session.get(User, int(user_id))

    from utils import category_icon, format_brl, format_date_br, generate_csrf_token, time_ago

    app.jinja_env.globals["csrf_token"] = generate_csrf_token
    # Versão dos arquivos estáticos (data da última modificação do CSS/JS),
    # usada como ?v=... nos links: quando o arquivo muda, o navegador do
    # usuário baixa a versão nova em vez de usar a antiga do cache.
    app.jinja_env.globals["asset_version"] = _static_version(app.static_folder)
    app.jinja_env.filters["category_icon"] = category_icon
    app.jinja_env.filters["brl"] = format_brl
    app.jinja_env.filters["time_ago"] = time_ago
    app.jinja_env.filters["date_br"] = format_date_br

    # Blueprints: cada um agrupa as rotas de um assunto (ver routes/).
    from routes.auth import auth_bp
    from routes.profile import profile_bp
    from routes.tasks import tasks_bp
    from routes.applications import applications_bp
    from routes.reviews import reviews_bp
    from routes.dashboard import dashboard_bp
    from routes.ai import ai_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(profile_bp, url_prefix="/perfil")
    app.register_blueprint(tasks_bp, url_prefix="/tarefas")
    app.register_blueprint(applications_bp, url_prefix="/candidaturas")
    app.register_blueprint(reviews_bp, url_prefix="/avaliacoes")
    app.register_blueprint(dashboard_bp, url_prefix="/painel")
    app.register_blueprint(ai_bp, url_prefix="/ai")

    @app.route("/")
    def home():
        # As 6 tarefas abertas mais recentes aparecem na home como destaque;
        # a listagem completa (com busca e filtro) fica em /tarefas.
        featured_tasks = (
            Task.query.filter_by(status=Task.STATUS_OPEN)
            .order_by(Task.created_at.desc())
            .limit(6)
            .all()
        )
        # Números reais da plataforma (não inventados) para a faixa de
        # prova social da home.
        stats = {
            "open_tasks": Task.query.filter_by(status=Task.STATUS_OPEN).count(),
            "done_tasks": Task.query.filter_by(status=Task.STATUS_DONE).count(),
            "providers": User.query.filter_by(is_provider=True).count(),
        }
        return render_template("index.html", featured_tasks=featured_tasks, stats=stats)

    def render_error(code):
        title, message = ERROR_PAGES[code]
        return render_template("errors/error.html", code=code, title=title, message=message), code

    @app.errorhandler(403)
    def forbidden(error):
        return render_error(403)

    @app.errorhandler(404)
    def not_found(error):
        return render_error(404)

    @app.errorhandler(413)
    def too_large(error):
        return render_error(413)

    @app.errorhandler(500)
    def server_error(error):
        # Uma exceção não tratada pode deixar a sessão do SQLAlchemy em um
        # estado inconsistente; sem o rollback, o próximo request nesse
        # mesmo worker herdaria uma transação quebrada.
        db.session.rollback()
        return render_error(500)

    return app


# Este bloco só roda com "python app.py". O modo debug (recarregamento
# automático + depurador interativo no navegador) só liga com FLASK_DEBUG=1
# no .env — o depurador permite executar código no servidor, então nunca
# pode ficar ativo fora da máquina de desenvolvimento.
if __name__ == "__main__":
    app = create_app()

    # RESET_DB_ON_START=1 no .env: cada "python app.py" começa com o banco
    # limpo e os dados de demonstração (útil para apresentações). O reset
    # acontece ao INICIAR, não ao fechar, porque Ctrl+C ou fechar o terminal
    # interrompe o processo sem garantia de rodar código de limpeza.
    # Com FLASK_DEBUG=1 o recarregador reinicia o servidor a cada arquivo
    # salvo (variável WERKZEUG_RUN_MAIN="true" no processo filho); só
    # resetamos na primeira inicialização, senão os dados sumiriam a cada edição.
    if os.environ.get("RESET_DB_ON_START") == "1" and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        from seed import seed_database

        with app.app_context():
            seed_database()

    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
