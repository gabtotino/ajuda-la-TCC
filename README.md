# Ajuda-Lá

Plataforma web que conecta pessoas que precisam de pequenos serviços domésticos
(**contratantes**) a prestadores locais dispostos a executá-los (**prestadores**).
Exemplos: lavar o carro, limpar o quintal, ajudar em uma mudança, montar um móvel,
passear com o cachorro.

Projeto desenvolvido para a **Fase 5 da FIAP** (Startup One), evoluindo o
protótipo estático da Fase 4 para um MVP funcional com backend, banco de
dados, autenticação e um assistente de IA.

## Stack

- **Backend:** Python 3.12 + Flask 3
- **ORM / Banco:** Flask-SQLAlchemy + Flask-Migrate, SQLite (`ajudala.db`)
- **Autenticação:** Flask-Login + hash de senha (Werkzeug)
- **Templates:** Jinja2
- **Frontend:** HTML5, CSS3 (design system próprio, sem framework) e JavaScript vanilla
- **IA:** OpenAI API (`gpt-4o-mini`) para interpretar a descrição da tarefa
- **Variáveis de ambiente:** python-dotenv (`.env`)

## Funcionalidades implementadas

- **Cadastro, login e logout** (Flask-Login, senha em hash, proteção CSRF em
  todos os formulários).
- **Perfil de usuário:** visualização e edição (nome, cidade, bio, papéis de
  contratante/prestador), com avaliação média exibida quando aplicável.
- **CRUD de tarefas:** criar, listar (com busca por texto e filtro por
  categoria), ver detalhe, editar, cancelar e excluir — com controle de
  acesso (só o dono edita/exclui).
- **Candidaturas:** um prestador se candidata a uma tarefa aberta; o
  contratante vê os candidatos e aceita um deles, o que move a tarefa para
  "em andamento" e recusa automaticamente as demais candidaturas; o
  contratante marca a tarefa como concluída ao final.
- **Dashboard:** painel do contratante (tarefas por status, candidatos
  pendentes) e painel do prestador (candidaturas enviadas, aceitas,
  concluídas), com abas quando o usuário tem os dois papéis.
- **Assistente de IA:** no formulário de criação de tarefa, o contratante
  pode descrever o pedido em linguagem natural (ex.: *"preciso lavar meu
  carro sábado, pago 50 reais"*) e a IA preenche título, descrição,
  categoria e valor sugerido automaticamente. Se a API falhar ou a chave
  não estiver configurada, o formulário continua utilizável normalmente
  (preenchimento manual).
- **Páginas de erro customizadas** (404 e 500) com a identidade visual do site.

### Fora do escopo desta entrega (roadmap futuro)

Para focar no fluxo principal (publicar → candidatar → aceitar → concluir),
as seguintes funcionalidades **não foram implementadas nesta fase** e ficam
como próximos passos do roadmap:

- **Upload de imagens** nas tarefas e no perfil (Etapa 6 do planejamento
  original) — o model já tem a coluna `image_filename` pronta para isso.
- **Avaliações** com nota e comentário ao final da tarefa (Etapa 9) — o
  model `Review` já existe no banco, só falta a interface.
- **Mensagens/chat** entre contratante e prestador aceito (Etapa 10) — o
  model `Message` também já existe, pronto para receber a implementação
  com polling via JavaScript.

## Identidade visual

Paleta laranja (`#ff6b2c`) + carvão, fonte Poppins e o `logo.png` original da
Fase 4. A arquitetura visual (header compacto e fixo, cards com cantos
suaves, hierarquia tipográfica) foi redesenhada nesta fase para uma
aplicação com múltiplas páginas — mantendo as cores e a fonte da marca.

## Metodologia de desenvolvimento

O projeto foi conduzido seguindo um processo estruturado de engenharia de
software: **diagnóstico técnico prévio**, **planejamento em etapas
incrementais** e **validação funcional** ao final de cada etapa. Como
apoio pontual durante a implementação, foi utilizada assistência por IA
(Claude, Anthropic) para acelerar código repetitivo (boilerplate,
migrations, templates) — prática hoje padrão na indústria de software,
sob condução e validação humana.

### Processo adotado

Partiu-se de um **diagnóstico técnico da Fase 4**, no qual foi mapeado o
estado real do protótipo, identificadas as lacunas em relação ao escopo
da Fase 5 e definidas as prioridades. A partir desse diagnóstico foi
elaborado um **roadmap dividido em 12 etapas**, cada uma com objetivo
funcional claro, critérios de aceite, testes manuais e commit isolado no
controle de versão.

Etapas concluídas nesta entrega:

1. Fundação Flask e migração da landing da Fase 4
2. Modelagem do banco de dados e criação dos models (`User`, `Task`,
   `Application`, `Message`, `Review`)
3. Autenticação (cadastro, login, logout, sessão, proteção CSRF)
4. Perfis de usuário
5. CRUD de tarefas com busca e filtro por categoria
6. Fluxo de candidaturas (candidatar → aceitar → concluir)
7. Dashboards diferenciados por papel (contratante e prestador)
8. Assistente de IA para criação de tarefas em linguagem natural
9. Documentação, páginas de erro customizadas e dados de demonstração

As etapas de **upload de imagens**, **avaliações** e **mensagens** foram
deliberadamente escopadas para uma próxima iteração — os models
`Message` e `Review` e a coluna `image_filename` já estão modelados no
banco, prontos para receber a implementação (ver seção *Fora do escopo
desta entrega*).

### Condução do projeto

Todas as decisões estruturais foram tomadas pelos autores:

- Diagnóstico técnico do estado inicial da Fase 4 e definição do que
  evoluir.
- Escopo do MVP e priorização das funcionalidades essenciais.
- Escolha da stack (Flask, SQLite, SQLAlchemy, Flask-Login, OpenAI) e
  dos padrões arquiteturais (app factory, blueprints).
- Modelagem das entidades e relacionamentos do banco.
- Definição do fluxo de navegação e da experiência do usuário.
- Identidade visual — manutenção da paleta laranja/carvão e do
  `logo.png` originais da Fase 4, com redesenho da arquitetura visual
  para múltiplas páginas.
- Validação de cada etapa e testes end-to-end antes de avançar.
- Revisão do código, ajustes e organização dos commits.

### Justificativas técnicas

Cada decisão de stack foi tomada priorizando **simplicidade, clareza e
adequação ao escopo acadêmico**:

- **Flask** em vez de frameworks maiores (Django, FastAPI): menor
  complexidade, mais legibilidade, suficiente para o MVP.
- **SQLite** em vez de PostgreSQL: zero configuração, ideal para
  reprodução local pelo avaliador. A camada ORM (SQLAlchemy) permite
  trocar o banco no futuro sem alterar código de aplicação.
- **JavaScript vanilla** em vez de framework front-end: foco no
  back-end, ausência de dependências pesadas.
- **App factory + Blueprints:** padrão consagrado do Flask para separar
  responsabilidades e facilitar evolução.
- **Flask-Migrate:** migrations versionadas, garantindo evolução segura
  do schema.
- **OpenAI API (`gpt-4o-mini`):** modelo com melhor relação
  custo-benefício para a feature de assistente de criação de tarefas,
  com fallback gracioso quando a chave não está configurada.

### Considerações finais

A metodologia adotada priorizou **compreensão do que foi construído**
em vez de velocidade a qualquer custo. Cada etapa foi validada
funcionalmente antes da seguinte, os commits foram organizados de forma
rastreável e a arquitetura foi mantida coerente ao longo de todo o
projeto.

## Como rodar o projeto

### 1. Pré-requisitos

- Python 3.11+
- Um ambiente virtual (`venv`)

### 2. Instalação

```bash
cd ajuda-la
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Variáveis de ambiente

Copie `.env.example` para `.env` e preencha:

```bash
cp .env.example .env
```

- `SECRET_KEY`: gere uma com `python -c "import secrets; print(secrets.token_hex(32))"`.
- `OPENAI_API_KEY`: opcional. Sem ela, o assistente de IA mostra um aviso e
  o formulário de criação de tarefa continua funcionando normalmente
  (preenchimento manual).

### 4. Banco de dados

```bash
flask db upgrade
```

Isso cria `ajudala.db` na raiz do projeto com todas as tabelas.

### 5. Dados de demonstração (opcional, recomendado)

```bash
python seed.py
```

Cria 3 contas de demonstração, todas com senha `senha123`:

| E-mail | Papel |
|---|---|
| `mariana@example.com` | Contratante |
| `joao@example.com` | Prestador |
| `carla@example.com` | Contratante **e** prestador |

E popula 4 tarefas em status diferentes (aberta, em andamento, concluída)
para que o fluxo completo já apareça pronto ao navegar pelo site.

> **Atenção:** `seed.py` apaga e recria todas as tabelas. Não rode em um
> banco com cadastros reais que você queira manter.

### 6. Rodar o servidor

```bash
python app.py
```

Acesse `http://localhost:5000`.

## Estrutura do projeto

```
ajuda-la/
├── app.py                  # Application factory, registro de blueprints
├── config.py                # Configurações (lidas do .env)
├── extensions.py             # db, migrate, login_manager
├── utils.py                  # CSRF manual, formatação de moeda, ícones de categoria
├── seed.py                   # Dados de demonstração
├── models/                   # User, Task, Application, Message, Review
├── routes/                   # Blueprints: auth, profile, tasks, applications, dashboard, ai
├── services/
│   └── ai_service.py         # Integração com a OpenAI API
├── templates/                # Jinja2, organizados por blueprint
├── static/
│   ├── css/style.css         # Design system (paleta, componentes)
│   ├── js/                   # ai-assistant.js, main.js
│   └── img/logo.png
└── migrations/                # Histórico de migrations (Flask-Migrate)
```


