# models/alert.py
"""Alerta interno do prestador: "me avise de tarefas desta categoria/cidade".

Não envia e-mail nem push (fora do escopo do MVP): as tarefas que batem
com os alertas aparecem no painel do prestador e como contador no menu.
Categoria e cidade são opcionais, mas pelo menos uma precisa existir.
"""

from datetime import datetime

from extensions import db


class Alert(db.Model):
    __tablename__ = "alerts"

    MAX_PER_USER = 5

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category = db.Column(db.String(80), nullable=True)
    city = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="alerts", lazy=True)

    @property
    def label(self):
        parts = [self.category or "Qualquer categoria", self.city or "qualquer cidade"]
        return " · ".join(parts)

    def matches(self, task):
        if self.category and task.category != self.category:
            return False
        if self.city and task.city.lower() != self.city.lower():
            return False
        return True
