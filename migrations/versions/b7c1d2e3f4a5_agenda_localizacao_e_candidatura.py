"""Agenda e localização estruturada nas tarefas; contexto na candidatura

- tasks: city, neighborhood, desired_date, time_period, is_flexible,
  requirements (location é migrado para city/neighborhood e removido)
- applications: message, proposed_value

Revision ID: b7c1d2e3f4a5
Revises: f539a2055e26
Create Date: 2026-11-02 10:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "b7c1d2e3f4a5"
down_revision = "f539a2055e26"
branch_labels = None
depends_on = None


def upgrade():
    # SQLite não suporta ALTER TABLE completo; batch_alter_table recria a
    # tabela por baixo dos panos quando necessário (ex.: drop_column).
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("city", sa.String(length=80), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("neighborhood", sa.String(length=80), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("desired_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("time_period", sa.String(length=20), nullable=False, server_default="qualquer"))
        batch_op.add_column(sa.Column("is_flexible", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("requirements", sa.Text(), nullable=True))

    # Migração de dados: "Bairro, Cidade" -> neighborhood / city. Um texto
    # sem vírgula vira só a cidade.
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, location FROM tasks")).fetchall()
    for task_id, location in rows:
        parts = [part.strip() for part in (location or "").split(",") if part.strip()]
        city = parts[-1] if parts else ""
        neighborhood = parts[0] if len(parts) > 1 else ""
        conn.execute(
            sa.text("UPDATE tasks SET city = :city, neighborhood = :neighborhood WHERE id = :id"),
            {"city": city, "neighborhood": neighborhood, "id": task_id},
        )

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("location")
        batch_op.create_index("ix_tasks_city", ["city"], unique=False)
        batch_op.create_index("ix_tasks_desired_date", ["desired_date"], unique=False)

    with op.batch_alter_table("applications") as batch_op:
        batch_op.add_column(sa.Column("message", sa.Text(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("proposed_value", sa.Numeric(precision=10, scale=2), nullable=True))


def downgrade():
    with op.batch_alter_table("applications") as batch_op:
        batch_op.drop_column("proposed_value")
        batch_op.drop_column("message")

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("location", sa.String(length=150), nullable=False, server_default=""))

    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE tasks SET location = CASE WHEN neighborhood != '' "
            "THEN neighborhood || ', ' || city ELSE city END"
        )
    )

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index("ix_tasks_desired_date")
        batch_op.drop_index("ix_tasks_city")
        batch_op.drop_column("requirements")
        batch_op.drop_column("is_flexible")
        batch_op.drop_column("time_period")
        batch_op.drop_column("desired_date")
        batch_op.drop_column("neighborhood")
        batch_op.drop_column("city")
