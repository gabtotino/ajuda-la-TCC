# models/task.py
"""Model da tarefa publicada por um contratante."""

from datetime import date, datetime

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

    STATUS_LABELS = {
        STATUS_OPEN: "Aberta",
        STATUS_IN_PROGRESS: "Em andamento",
        STATUS_DONE: "Concluída",
        STATUS_CANCELED: "Cancelada",
    }

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

    # Período do dia em que o contratante quer o serviço. Guardamos um
    # código curto e exibimos o rótulo — assim o texto pode mudar sem
    # precisar de migration.
    TIME_PERIODS = {
        "manha": "Manhã",
        "tarde": "Tarde",
        "noite": "Noite",
        "qualquer": "Qualquer horário",
    }

    # Tarefas com data desejada até N dias à frente recebem o selo
    # "Urgente" nos cards — calculado, não armazenado, para nunca ficar
    # desatualizado.
    URGENT_WITHIN_DAYS = 2

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(80), nullable=False, index=True)

    # Localização estruturada (antes era um único campo de texto livre):
    # separar cidade e bairro permite filtrar a listagem por cada um.
    city = db.Column(db.String(80), nullable=False, index=True)
    neighborhood = db.Column(db.String(80), nullable=False, default="")

    # Agenda: data desejada (opcional no banco por causa das tarefas
    # antigas, obrigatória no formulário), período e se há flexibilidade.
    desired_date = db.Column(db.Date, nullable=True, index=True)
    time_period = db.Column(db.String(20), nullable=False, default="qualquer")
    is_flexible = db.Column(db.Boolean, nullable=False, default=False)

    # Numeric garante precisão decimal exata para valores em reais.
    # Float sofreria com arredondamento binário (ex.: 0.1 + 0.2 != 0.3 em
    # ponto flutuante), o que é inaceitável quando o campo é dinheiro.
    value = db.Column(db.Numeric(10, 2), nullable=False)

    status = db.Column(db.String(20), nullable=False, default=STATUS_OPEN)

    MAX_IMAGES = 3

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

    # cascade="all, delete-orphan": ao excluir a tarefa, o SQLAlchemy apaga
    # junto candidaturas, mensagens e avaliação, sem deixar linhas órfãs
    # apontando para um task_id que não existe mais.
    applications = db.relationship(
        "Application",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Application.created_at",
        lazy=True,
    )
    messages = db.relationship(
        "Message", back_populates="task", cascade="all, delete-orphan", lazy=True
    )
    review = db.relationship(
        "Review",
        back_populates="task",
        cascade="all, delete-orphan",
        uselist=False,
        lazy=True,
    )
    images = db.relationship(
        "TaskImage",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskImage.position",
        lazy=True,
    )
    saved_by = db.relationship(
        "SavedTask", back_populates="task", cascade="all, delete-orphan", lazy=True
    )

    @property
    def cover_image(self):
        return self.images[0] if self.images else None

    def is_chat_participant(self, user):
        """Chat existe só depois do aceite, entre contratante e prestador escolhido."""
        if not user or not user.is_authenticated or not self.accepted_provider_id:
            return False
        return user.id in (self.contractor_id, self.accepted_provider_id)

    @property
    def chat_is_open(self):
        # Durante a execução dá para conversar; depois de concluída a
        # conversa fica disponível só para leitura (histórico).
        return self.status == self.STATUS_IN_PROGRESS

    @property
    def location_label(self):
        """'Bairro, Cidade' (ou só a cidade, quando não há bairro)."""
        if self.neighborhood:
            return f"{self.neighborhood}, {self.city}"
        return self.city

    @property
    def time_period_label(self):
        return self.TIME_PERIODS.get(self.time_period, "Qualquer horário")

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)

    @property
    def is_urgent(self):
        if self.status != self.STATUS_OPEN or not self.desired_date:
            return False
        days_left = (self.desired_date - date.today()).days
        return 0 <= days_left <= self.URGENT_WITHIN_DAYS

    def is_involved(self, user):
        """Contratante, prestador aceito ou alguém que se candidatou."""
        if not user or not user.is_authenticated:
            return False
        if user.id in (self.contractor_id, self.accepted_provider_id):
            return True
        return any(a.provider_id == user.id for a in self.applications)

    def can_be_viewed_by(self, user):
        # Tarefa aberta é pública; depois de encerrada, só os envolvidos
        # continuam vendo os detalhes (endereço, candidatos, avaliação...).
        return self.status == self.STATUS_OPEN or self.is_involved(user)

    def __repr__(self):
        return f"<Task {self.id} {self.title!r}>"
