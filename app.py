# app.py
"""Ponto de entrada da aplicação Ajuda-Lá."""

from flask import Flask, render_template

from config import Config
from extensions import db, login_manager, migrate


def create_app():
    """Application factory: monta e configura a instância do Flask.

    Usamos uma factory (em vez de criar `app = Flask(__name__)` direto no
    módulo, como na Etapa 1) por dois motivos: evita import circular quando
    models e rotas também precisam importar `db` a partir deste arquivo, e
    permite criar múltiplas instâncias da aplicação — por exemplo, uma
    apontando para um banco de teste isolado, sem afetar o banco de
    desenvolvimento.
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # Liga as extensões (SQLAlchemy, Migrate) a esta instância específica
    # do app. Elas foram criadas "vazias" em extensions.py justamente para
    # serem inicializadas aqui.
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Rota para onde o Flask-Login redireciona quando um usuário anônimo
    # tenta acessar uma página marcada com @login_required (usado a partir
    # da Etapa 4, em rotas de perfil/dashboard).
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para continuar."
    login_manager.login_message_category = "info"

    # Importa os models dentro da factory (não no topo do arquivo) para
    # que o Flask-Migrate só tente carregá-los depois que db.init_app já
    # rodou. O import em si não é usado diretamente aqui: ele existe para
    # registrar as classes User/Task/Application/Message/Review no
    # metadata do SQLAlchemy, que é o que "flask db migrate" inspeciona.
    from models import Application, Message, Review, Task, User  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        # Flask-Login chama esta função em toda request autenticada,
        # passando o valor salvo na sessão (get_id(), via UserMixin) para
        # recarregar o objeto User completo a partir do banco.
        # db.session.get() é a forma recomendada no SQLAlchemy 2.0 para
        # buscar por chave primária (Query.get() está depreciado).
        return db.session.get(User, int(user_id))

    # Registra o token CSRF (utils.py) como função global do Jinja2, para
    # que qualquer template possa chamar {{ csrf_token() }} sem import.
    from utils import generate_csrf_token

    app.jinja_env.globals["csrf_token"] = generate_csrf_token

    # Blueprints: cada um agrupa as rotas de um assunto (ver routes/).
    from routes.auth import auth_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")

    @app.route("/")
    def home():
        return render_template("index.html")

    return app


# Instância usada pelo comando "flask" (que procura automaticamente por uma
# variável chamada "app" em app.py) e pelas migrations do Flask-Migrate.
app = create_app()

# Este bloco só roda quando executamos "python app.py" diretamente.
# debug=True recarrega o servidor automaticamente ao salvar arquivos
# e mostra erros detalhados no navegador. NUNCA use debug=True em produção.
if __name__ == "__main__":
    app.run(debug=True)
