# models/task.py
"""Model da tarefa publicada por um contratante."""

from datetime import datetime

from extensions import db


class Task(db.Model):
    __tablename__ = "tasks"

    # Estados possíveis do ciclo de vida de uma tarefa. Usamos constantes de
    # string simples (em vez do tipo Enum nativo do SQLAlchemy) porque o
    # SQLite não tem um tipo ENUM real — na prática o SQLAlchemy simularia
    # isso com uma CHECK constraint de qualquer forma. Strings são mais
    # fáceis de depurar no DB Browser e de estender no futuro.
    STATUS_OPEN = "aberta"
    STATUS_IN_PROGRESS = "em_andamento"
    STATUS_DONE = "concluida"
    STATUS_CANCELED = "cancelada"
    STATUSES = (STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_DONE, STATUS_CANCELED)

    # Categorias fixas (em vez de texto livre) para que o filtro da
    # listagem e o assistente de IA (Etapa 11) sempre trabalhem com o
    # mesmo vocabulário.
    CATEGORIES = (
        "Lavagem de veículo",
        "Limpeza de quintal",
        "Mudança",
        "Montagem de móveis",
        "Passeio com pet",
        "Pintura",
        "Reparos domésticos",
        "Limpeza doméstica",
        "Aulas particulares",
        "Outros",
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    location = db.Column(db.String(150), nullable=False)

    # Numeric garante precisão decimal exata para valores em reais.
    # Float sofreria com arredondamento binário (ex.: 0.1 + 0.2 != 0.3 em
    # ponto flutuante), o que é inaceitável quando o campo é dinheiro.
    value = db.Column(db.Numeric(10, 2), nullable=False)

    status = db.Column(db.String(20), nullable=False, default=STATUS_OPEN)
    image_filename = db.Column(db.String(255), nullable=True)

    contractor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    accepted_provider_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        # Constraint no nível do banco: mesmo que um bug na aplicação tente
        # gravar um status inválido, o SQLite recusa o INSERT/UPDATE.
        db.CheckConstraint(
            "status IN ('aberta','em_andamento','concluida','cancelada')",
            name="ck_tasks_status_valido",
        ),
    )

    # O relacionamento "contractor" já foi declarado no model User (via
    # backref em tasks_created). Aqui só precisamos do lado do prestador
    # aceito, que é opcional (nullable) até alguém ser aprovado na Etapa 7.
    accepted_provider = db.relationship(
        "User", foreign_keys=[accepted_provider_id], lazy=True
    )

    def __repr__(self):
        return f"<Task {self.id} {self.title!r}>"
