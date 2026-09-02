# models/__init__.py
"""Agrega os models em um único ponto de importação.

Além de deixar `from models import User, Task` mais curto nas rotas,
isso garante que TODOS os models sejam carregados quando este pacote é
importado — o que é essencial para o Flask-Migrate conseguir enxergar
todas as tabelas na hora de gerar uma migration (`flask db migrate`).
Se um model não for importado em algum lugar, o SQLAlchemy nunca fica
sabendo que ele existe.
"""

from models.user import User
from models.task import Task
from models.application import Application
from models.message import Message
from models.review import Review

__all__ = ["User", "Task", "Application", "Message", "Review"]
