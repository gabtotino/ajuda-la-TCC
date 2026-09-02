# seed.py
"""Script para popular o banco com dados de demonstração (apresentação/vídeo).

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

    mariana = User(
        name="Mariana Souza",
        email="mariana@example.com",
        is_contractor=True,
        city="São Paulo, SP",
        bio="Moro na Vila Mariana e sempre preciso de uma força com tarefas de casa.",
    )
    mariana.set_password("senha123")

    joao = User(
        name="João Pereira",
        email="joao@example.com",
        is_provider=True,
        city="São Paulo, SP",
        bio="Faço serviços domésticos com pontualidade e capricho. Disponível fins de semana.",
    )
    joao.set_password("senha123")

    # Usuário com os dois papéis, para demonstrar o painel com abas.
    carla = User(
        name="Carla Nunes",
        email="carla@example.com",
        is_contractor=True,
        is_provider=True,
        city="Osasco, SP",
        bio="Às vezes contrato ajuda, às vezes ofereço — moro perto e gosto de ajudar a vizinhança.",
        avg_rating=4.5,
    )
    carla.set_password("senha123")

    db.session.add_all([mariana, joao, carla])
    # Commit aqui é necessário para que os ids existam antes de usá-los
    # como foreign key nas tarefas abaixo.
    db.session.commit()

    task_open_1 = Task(
        title="Lavar carro no sábado",
        description="Preciso lavar meu carro (hatch) na garagem de casa, sábado de manhã.",
        category="Lavagem de veículo",
        location="Vila Mariana, São Paulo",
        value=50.00,
        status=Task.STATUS_OPEN,
        contractor_id=mariana.id,
    )
    task_open_2 = Task(
        title="Cortar grama e organizar quintal",
        description="Quintal pequeno, grama alta e alguns galhos para recolher.",
        category="Limpeza de quintal",
        location="Pinheiros, São Paulo",
        value=80.00,
        status=Task.STATUS_OPEN,
        contractor_id=carla.id,
    )
    task_in_progress = Task(
        title="Montar guarda-roupa novo",
        description="Guarda-roupa de 3 portas comprado desmontado, já tenho as ferramentas.",
        category="Montagem de móveis",
        location="Osasco, São Paulo",
        value=90.00,
        status=Task.STATUS_IN_PROGRESS,
        contractor_id=carla.id,
        accepted_provider_id=joao.id,
    )
    task_done = Task(
        title="Passear com cachorro à tarde",
        description="Passeio de 30 minutos com meu cachorro, todo dia às 17h durante a semana.",
        category="Passeio com pet",
        location="Vila Mariana, São Paulo",
        value=35.00,
        status=Task.STATUS_DONE,
        contractor_id=mariana.id,
        accepted_provider_id=joao.id,
    )
    db.session.add_all([task_open_1, task_open_2, task_in_progress, task_done])
    db.session.commit()

    # João já se candidatou à primeira tarefa aberta da Mariana, e foi
    # aceito nas outras duas (uma em andamento, uma concluída) — dá pra
    # mostrar os três estados de uma candidatura na demonstração.
    applications = [
        Application(task_id=task_open_1.id, provider_id=joao.id, status=Application.STATUS_PENDING),
        Application(task_id=task_in_progress.id, provider_id=joao.id, status=Application.STATUS_ACCEPTED),
        Application(task_id=task_done.id, provider_id=joao.id, status=Application.STATUS_ACCEPTED),
    ]
    db.session.add_all(applications)
    db.session.commit()

    print("Seed concluído. Contas de demonstração (senha 'senha123' para todas):")
    print(f"  Contratante:            {mariana.email}")
    print(f"  Prestador:              {joao.email}")
    print(f"  Contratante + Prestador: {carla.email}")
