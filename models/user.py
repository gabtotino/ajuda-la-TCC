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

    # Última vez que o prestador viu as tarefas dos seus alertas: o que foi
    # publicado depois disso conta como "novo" no menu e no painel.
    alerts_seen_at = db.Column(db.DateTime, nullable=True)
    alerts = db.relationship(
        "Alert", back_populates="user", cascade="all, delete-orphan", lazy=True
    )

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

    @property
    def completed_tasks_count(self):
        """Tarefas concluídas como prestador — sinal de confiança no perfil."""
        from models.task import Task

        return Task.query.filter_by(
            accepted_provider_id=self.id, status=Task.STATUS_DONE
        ).count()

    @property
    def review_count(self):
        return len(self.reviews_received)

    @property
    def short_bio(self):
        if not self.bio:
            return ""
        return self.bio if len(self.bio) <= 140 else self.bio[:137].rstrip() + "..."

    def recalculate_rating(self):
        """Atualiza avg_rating a partir das avaliações recebidas.

        Chamado logo depois de criar uma Review, na mesma transação, para
        que média e lista de avaliações nunca fiquem divergentes.
        """
        from models.review import Review

        # Consulta direta (em vez da lista reviews_received já carregada em
        # memória) para incluir a avaliação recém-criada na mesma transação.
        average = (
            db.session.query(db.func.avg(Review.rating))
            .filter(Review.reviewed_id == self.id)
            .scalar()
        )
        self.avg_rating = round(float(average), 2) if average is not None else 0.0

    def __repr__(self):
        return f"<User {self.id} {self.email}>"
