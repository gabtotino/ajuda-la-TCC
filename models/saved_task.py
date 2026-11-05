# models/saved_task.py
"""Tarefas que um prestador salvou para decidir depois."""

from datetime import datetime

from extensions import db


class SavedTask(db.Model):
    __tablename__ = "saved_tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    task = db.relationship("Task", back_populates="saved_by", lazy=True)

    __table_args__ = (
        # Salvar duas vezes a mesma tarefa não faz sentido; o banco garante.
        db.UniqueConstraint("user_id", "task_id", name="uq_saved_task_user_task"),
    )
