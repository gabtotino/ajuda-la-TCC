# models/user.py
"""Model do usuário: representa tanto contratantes quanto prestadores.

Em vez de duas tabelas separadas (ou de herança de tabelas), usamos duas
colunas booleanas (is_contractor / is_provider) na mesma tabela `users`.
Isso permite que uma mesma pessoa publique tarefas E se candidate a
tarefas de outros usuários, sem duplicar cadastro, e evita joins extras
só para descobrir "quem é o quê" — decisão de modelagem deliberadamente
simples para o escopo do MVP.
"""

from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(UserMixin, db.Model):
    # UserMixin (Flask-Login) implementa is_authenticated, is_active,
    # is_anonymous e get_id() a partir da coluna "id" abaixo, sem precisar
    # reescrever esses métodos manualmente.
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    # Nunca guardamos a senha em texto puro: apenas o hash gerado por
    # set_password(). password_hash do Werkzeug já embute o algoritmo,
    # o salt e o custo — não precisamos de uma coluna de salt separada.
    password_hash = db.Column(db.String(255), nullable=False)

    # Um usuário pode acumular os dois papéis ao longo do tempo; o
    # cadastro (Etapa 3) decide os valores iniciais, mas nada impede um
    # contratante também virar prestador depois, editando o perfil.
    is_contractor = db.Column(db.Boolean, default=False, nullable=False)
    is_provider = db.Column(db.Boolean, default=False, nullable=False)

    bio = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(120), nullable=True)

    # Média das notas recebidas como prestador. Guardamos o valor já
    # calculado (em vez de agregar a tabela Review toda vez que o perfil é
    # aberto) porque avg_rating é lido com muito mais frequência do que é
    # atualizado — só muda quando uma nova Review é criada (Etapa 9).
    avg_rating = db.Column(db.Float, default=0.0, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # --- Relacionamentos ---
    # Tarefas publicadas por este usuário como contratante. O outro lado
    # (accepted_provider) é declarado diretamente no model Task, porque
    # duas foreign keys de Task apontam para users.id e o SQLAlchemy
    # precisa saber qual delas usar em cada relationship.
    tasks_created = db.relationship(
        "Task",
        foreign_keys="Task.contractor_id",
        backref="contractor",
        lazy=True,
    )

    def set_password(self, raw_password):
        """Gera e armazena o hash da senha informada no cadastro."""
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        """Confere se a senha digitada no login bate com o hash salvo."""
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self):
        return f"<User {self.id} {self.email}>"
