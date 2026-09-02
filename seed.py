# seed.py
"""Script opcional para popular o banco com dados de teste/demonstração.

Rode com:
    python seed.py

Atenção: ele APAGA e recria todas as tabelas antes de inserir os dados.
Nunca rode em um banco que já tenha cadastros reais que você queira manter.
"""

from app import create_app
from extensions import db
from models import Application, Task, User

app = create_app()

with app.app_context():
    # Recomeça do zero para evitar duplicar dados a cada execução.
    db.drop_all()
    db.create_all()

    contractor = User(
        name="Mariana Souza",
        email="mariana@example.com",
        is_contractor=True,
        city="São Paulo",
    )
    contractor.set_password("senha123")

    provider = User(
        name="João Pereira",
        email="joao@example.com",
        is_provider=True,
        city="São Paulo",
        bio="Faço serviços domésticos com pontualidade e capricho.",
    )
    provider.set_password("senha123")

    db.session.add_all([contractor, provider])
    # Commit aqui é necessário para que contractor.id e provider.id sejam
    # gerados pelo banco antes de usá-los como foreign key abaixo.
    db.session.commit()

    task = Task(
        title="Lavar carro no sábado",
        description="Preciso lavar meu carro (hatch) na garagem de casa, sábado de manhã.",
        category="Lavagem de veículo",
        location="Vila Mariana, São Paulo",
        value=50.00,
        status=Task.STATUS_OPEN,
        contractor_id=contractor.id,
    )
    db.session.add(task)
    db.session.commit()

    application = Application(task_id=task.id, provider_id=provider.id)
    db.session.add(application)
    db.session.commit()

    print("Seed concluído:")
    print(f"  Contratante: {contractor.email} / senha123")
    print(f"  Prestador:   {provider.email} / senha123")
    print(f"  Tarefa criada: {task.title!r} (id={task.id})")
