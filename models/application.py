# models/application.py
"""Model da candidatura de um prestador a uma tarefa."""

from datetime import datetime

from extensions import db


class Application(db.Model):
    __tablename__ = "applications"

    STATUS_PENDING = "pendente"
    STATUS_ACCEPTED = "aceita"
    STATUS_REJECTED = "recusada"
    STATUSES = (STATUS_PENDING, STATUS_ACCEPTED, STATUS_REJECTED)

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)

    # Contexto para o contratante comparar candidatos antes de aceitar:
    # uma apresentação curta (obrigatória) e um valor proposto (opcional,
    # quando o prestador quer negociar o valor anunciado).
    message = db.Column(db.Text, nullable=False, default="")
    proposed_value = db.Column(db.Numeric(10, 2), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    task = db.relationship("Task", back_populates="applications", lazy=True)
    provider = db.relationship("User", backref="applications_sent", lazy=True)

    __table_args__ = (
        # Garante, no nível do banco, que um prestador não se candidate duas
        # vezes à mesma tarefa — regra de negócio central da Etapa 7. Fazer
        # isso só na rota seria menos seguro: dois requests simultâneos
        # poderiam passar pela checagem em Python antes de qualquer um
        # commitar, e a constraint do banco é a última linha de defesa.
        db.UniqueConstraint(
            "task_id", "provider_id", name="uq_application_task_provider"
        ),
        db.CheckConstraint(
            "status IN ('pendente','aceita','recusada')",
            name="ck_applications_status_valido",
        ),
    )

    def __repr__(self):
        return f"<Application task={self.task_id} provider={self.provider_id} {self.status}>"
