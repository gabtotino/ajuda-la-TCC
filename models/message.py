# models/message.py
"""Model das mensagens do chat 1:1 vinculado a uma tarefa (Etapa 10)."""

from datetime import datetime

from extensions import db


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    task = db.relationship("Task", backref="messages", lazy=True)
    sender = db.relationship("User", backref="messages_sent", lazy=True)

    def __repr__(self):
        return f"<Message task={self.task_id} sender={self.sender_id}>"
