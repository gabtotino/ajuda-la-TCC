# config.py
"""Configurações centrais da aplicação Ajuda-Lá."""

import os

from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente do processo Python.
# Precisa rodar antes da classe Config ler os valores com os.environ.
load_dotenv()

# Caminho absoluto da pasta do projeto, usado para localizar o arquivo do banco.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configurações compartilhadas por toda a aplicação."""

    # Chave usada pelo Flask para assinar sessões e tokens CSRF. Sem valor
    # padrão de propósito: create_app() recusa iniciar sem ela, para que
    # nenhum ambiente rode com uma chave fixa e pública.
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Cookie de sessão inacessível ao JavaScript e não enviado em requests
    # vindos de outros sites (camada extra contra CSRF).
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # URI de conexão do SQLAlchemy. sqlite:/// + caminho absoluto garante que
    # o banco seja encontrado independentemente de onde o comando é executado.
    # Usamos "or" (e não o segundo argumento de os.environ.get) porque o
    # .env define DATABASE_URL="" vazio por padrão — get() retornaria essa
    # string vazia em vez de cair no valor default.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        f"sqlite:///{os.path.join(BASE_DIR, 'ajudala.db')}"
    )

    # Desliga o rastreamento de modificações do SQLAlchemy: recurso que
    # consome memória extra e que este projeto não usa.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Pasta onde as imagens de tarefas/avatares serão salvas (a partir da Etapa 6).
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

    # Limite de tamanho de upload: 5 MB, conforme especificação do projeto.
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    # Chave da API da OpenAI, usada a partir da Etapa 11.
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

    # Tarefas por página na listagem pública.
    TASKS_PER_PAGE = 9


class TestConfig(Config):
    """Configuração usada pela suíte de testes (pytest)."""

    TESTING = True
    SECRET_KEY = "chave-de-teste"
    SQLALCHEMY_DATABASE_URI = "sqlite://"  # banco em memória, isolado por teste
    OPENAI_API_KEY = None
