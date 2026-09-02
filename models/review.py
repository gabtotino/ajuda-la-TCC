# models/review.py
"""Model da avaliação que o contratante deixa para o prestador ao final da tarefa."""

from datetime import datetime

from extensions import db


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)

    # unique=True: cada tarefa concluída só pode gerar UMA avaliação.
    task_id = db.Column(
        db.Integer, db.ForeignKey("tasks.id"), unique=True, nullable=False
    )
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reviewed_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    task = db.relationship(
        "Task", backref=db.backref("review", uselist=False), lazy=True
    )
    reviewer = db.relationship(
        "User", foreign_keys=[reviewer_id], backref="reviews_given", lazy=True
    )
    reviewed = db.relationship(
        "User", foreign_keys=[reviewed_id], backref="reviews_received", lazy=True
    )

    __table_args__ = (
        db.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
    )

    def __repr__(self):
        return f"<Review task={self.task_id} rating={self.rating}>"
