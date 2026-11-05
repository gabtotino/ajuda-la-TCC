# models/task_image.py
"""Imagens anexadas a uma tarefa (até 3 por tarefa).

Uma tabela própria, em vez da antiga coluna Task.image_filename, porque
uma tarefa pode ter várias imagens. Só o nome do arquivo (aleatório,
gerado pelo servidor) fica no banco; o arquivo em si vai para
static/uploads/tasks/ (ver services/upload_service.py).
"""

from datetime import datetime

from extensions import db


class TaskImage(db.Model):
    __tablename__ = "task_images"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
    filename = db.Column(db.String(64), nullable=False, unique=True)
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    task = db.relationship("Task", back_populates="images", lazy=True)

    def __repr__(self):
        return f"<TaskImage task={self.task_id} {self.filename}>"
