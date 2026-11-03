# seed.py
"""Script para popular o banco com dados de demonstração (apresentação/vídeo).

Rode com:
    python seed.py

Atenção: ele APAGA e recria todas as tabelas antes de inserir os dados.
Nunca rode em um banco que já tenha cadastros reais que você queira manter.
"""

from datetime import date, datetime, timedelta

from app import create_app
from extensions import db
from models import Application, Review, Task, User

app = create_app()

TODAY = date.today()
NOW = datetime.utcnow()


def make_user(name, email, city, bio, contractor=False, provider=False, days_ago=120):
    user = User(
        name=name,
        email=email,
        city=city,
        bio=bio,
        is_contractor=contractor,
        is_provider=provider,
        created_at=NOW - timedelta(days=days_ago),
    )
    user.set_password("senha123")
    return user


def make_task(contractor, title, description, category, city, neighborhood, value,
              days_ahead, period="qualquer", flexible=False, requirements=None,
              status=Task.STATUS_OPEN, provider=None, hours_ago=5):
    return Task(
        title=title,
        description=description,
        requirements=requirements,
        category=category,
        city=city,
        neighborhood=neighborhood,
        value=value,
        desired_date=TODAY + timedelta(days=days_ahead),
        time_period=period,
        is_flexible=flexible,
        status=status,
        contractor_id=contractor.id,
        accepted_provider_id=provider.id if provider else None,
        created_at=NOW - timedelta(hours=hours_ago),
    )


with app.app_context():
    # Recomeça do zero para evitar duplicar dados a cada execução.
    db.drop_all()
    db.create_all()

    mariana = make_user(
        "Mariana Souza", "mariana@example.com", "São Paulo",
        "Moro na Vila Mariana com meu cachorro e sempre preciso de uma força com tarefas de casa.",
        contractor=True,
    )
    joao = make_user(
        "João Pereira", "joao@example.com", "São Paulo",
        "Faço serviços domésticos com pontualidade e capricho. Tenho ferramentas próprias e "
        "experiência com montagem de móveis e pequenos reparos.",
        provider=True, days_ago=300,
    )
    carla = make_user(
        "Carla Nunes", "carla@example.com", "Osasco",
        "Às vezes contrato ajuda, às vezes ofereço — moro perto e gosto de ajudar a vizinhança.",
        contractor=True, provider=True, days_ago=200,
    )
    rafael = make_user(
        "Rafael Lima", "rafael@example.com", "São Paulo",
        "Estudante de educação física, adoro animais. Disponível à tarde e nos fins de semana.",
        provider=True, days_ago=40,
    )
    db.session.add_all([mariana, joao, carla, rafael])
    db.session.commit()

    # --- Tarefas abertas (aparecem na listagem pública) ---
    car = make_task(
        mariana, "Lavar carro no sábado",
        "Preciso lavar meu carro (hatch) na garagem de casa. Tenho mangueira e balde; "
        "falta só quem faça com capricho, por dentro e por fora.",
        "Lavagem de veículo", "São Paulo", "Vila Mariana", 60.00, days_ahead=1, period="manha",
        requirements="Trazer produtos de limpeza automotiva.", hours_ago=3,
    )
    yard = make_task(
        carla, "Cortar grama e organizar quintal",
        "Quintal pequeno, grama alta e alguns galhos para recolher e ensacar.",
        "Limpeza de quintal", "Osasco", "Centro", 90.00, days_ahead=4, period="manha", flexible=True,
        hours_ago=20,
    )
    painting = make_task(
        mariana, "Pintar muro da garagem",
        "Muro de aproximadamente 6 metros, tinta já comprada (branca). Precisa raspar partes descascadas antes.",
        "Pintura", "São Paulo", "Vila Mariana", 180.00, days_ahead=8, period="qualquer", flexible=True,
        requirements="Experiência com pintura; trazer rolo e pincéis.", hours_ago=30,
    )
    dog = make_task(
        carla, "Passear com cachorro à tarde",
        "Golden retriever dócil, passeio de 40 minutos pelo bairro durante a semana.",
        "Passeio com pet", "Osasco", "Bela Vista", 35.00, days_ahead=2, period="tarde", hours_ago=50,
    )
    moving = make_task(
        mariana, "Ajuda para carregar caixas na mudança",
        "Mudança de apartamento no mesmo prédio: cerca de 20 caixas e alguns móveis leves.",
        "Mudança", "São Paulo", "Moema", 150.00, days_ahead=12, period="manha", hours_ago=70,
    )
    # --- Tarefas com histórico (só aparecem para os envolvidos) ---
    wardrobe = make_task(
        carla, "Montar guarda-roupa novo",
        "Guarda-roupa de 3 portas comprado desmontado.",
        "Montagem de móveis", "Osasco", "Centro", 110.00, days_ahead=1, period="tarde",
        status=Task.STATUS_IN_PROGRESS, provider=joao, hours_ago=90,
    )
    shelf = make_task(
        mariana, "Montar estante de livros",
        "Estante de 5 prateleiras, veio com manual e todos os parafusos.",
        "Montagem de móveis", "São Paulo", "Vila Mariana", 80.00, days_ahead=-10,
        status=Task.STATUS_DONE, provider=joao, hours_ago=400,
    )
    faucet = make_task(
        carla, "Trocar torneira da cozinha",
        "Torneira nova já comprada, só precisa instalar.",
        "Reparos domésticos", "Osasco", "Centro", 70.00, days_ahead=-20,
        status=Task.STATUS_DONE, provider=joao, hours_ago=700,
    )
    walk_done = make_task(
        mariana, "Passeio com cachorro no fim de semana",
        "Dois passeios de 30 minutos no sábado.",
        "Passeio com pet", "São Paulo", "Vila Mariana", 40.00, days_ahead=-5,
        status=Task.STATUS_DONE, provider=rafael, hours_ago=200,
    )
    db.session.add_all([car, yard, painting, dog, moving, wardrobe, shelf, faucet, walk_done])
    db.session.commit()

    # --- Candidaturas com contexto (mensagem e valor proposto) ---
    db.session.add_all([
        Application(task_id=car.id, provider_id=joao.id,
                    message="Já lavei vários carros no bairro, levo aspirador portátil e produtos próprios. "
                            "Consigo chegar às 8h.",
                    created_at=NOW - timedelta(hours=2)),
        Application(task_id=car.id, provider_id=rafael.id,
                    message="Moro a 10 minutos e estou livre no sábado de manhã. Faço com calma e cuidado.",
                    proposed_value=50.00, created_at=NOW - timedelta(hours=1)),
        Application(task_id=car.id, provider_id=carla.id,
                    message="Posso ajudar! Só consigo depois das 10h, se não tiver problema.",
                    proposed_value=70.00, created_at=NOW - timedelta(minutes=30)),
        Application(task_id=yard.id, provider_id=joao.id,
                    message="Tenho roçadeira e sacos de lixo, resolvo em uma manhã.",
                    proposed_value=100.00, created_at=NOW - timedelta(hours=10)),
        Application(task_id=wardrobe.id, provider_id=joao.id, status=Application.STATUS_ACCEPTED,
                    message="Monto guarda-roupas com frequência, levo parafusadeira."),
        Application(task_id=shelf.id, provider_id=joao.id, status=Application.STATUS_ACCEPTED,
                    message="Faço a montagem em cerca de 1 hora."),
        Application(task_id=faucet.id, provider_id=joao.id, status=Application.STATUS_ACCEPTED,
                    message="Já instalei várias torneiras, levo veda-rosca."),
        Application(task_id=walk_done.id, provider_id=rafael.id, status=Application.STATUS_ACCEPTED,
                    message="Amo cachorros e moro perto, posso fazer os dois passeios."),
    ])

    # --- Avaliações das tarefas concluídas ---
    db.session.add_all([
        Review(task_id=shelf.id, reviewer_id=mariana.id, reviewed_id=joao.id, rating=5,
               comment="Pontual, cuidadoso e deixou tudo limpo. Recomendo!",
               created_at=NOW - timedelta(days=9)),
        Review(task_id=faucet.id, reviewer_id=carla.id, reviewed_id=joao.id, rating=4,
               comment="Resolveu rápido, só chegou um pouco atrasado.",
               created_at=NOW - timedelta(days=19)),
    ])
    # walk_done fica sem avaliação de propósito: aparece no painel da Mariana
    # como "próximo passo: avalie quem te ajudou".
    db.session.commit()

    for user in (joao, rafael, carla):
        user.recalculate_rating()
    db.session.commit()

    print("Seed concluído. Contas de demonstração (senha 'senha123' para todas):")
    print(f"  Contratante:              {mariana.email}")
    print(f"  Prestador (com histórico): {joao.email}")
    print(f"  Prestador (novo):          {rafael.email}")
    print(f"  Contratante + prestadora:  {carla.email}")
