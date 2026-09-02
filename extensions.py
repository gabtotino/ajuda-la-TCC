# extensions.py
"""Instâncias únicas das extensões Flask usadas pelo projeto.

Ficam em um módulo separado, sem importar `app` nenhum, justamente para
que outros módulos (models, routes) possam importar `db` sem criar uma
dependência circular com app.py, que é quem monta a aplicação através da
função create_app().
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()
