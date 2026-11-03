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
  todos os formulários, logout via `POST`, retorno seguro à página de origem
  após o login).
- **Perfil de usuário:** visualização e edição (nome, cidade, bio, papéis de
  contratante/prestador). Prestadores exibem média, número de avaliações,
  tarefas concluídas e a lista de avaliações recebidas.
- **Tarefas com agenda e localização estruturada:** título, descrição,
  requisitos, categoria, **cidade e bairro**, **data desejada, período e
  flexibilidade**, valor. Edição, cancelamento e exclusão só pelo dono.
- **Busca e organização:** a listagem pública mostra **apenas tarefas
  abertas**, com filtros por cidade, bairro, categoria, faixa de valor e
  data; ordenação (recentes, menor/maior valor, data mais próxima);
  paginação; tempo relativo ("publicada há 2 horas") e selo de urgência.
  Tarefas encerradas só aparecem para os envolvidos.
- **Candidaturas com contexto:** o prestador envia uma apresentação curta
  (obrigatória) e pode propor outro valor. O contratante compara os
  candidatos lado a lado — cidade, bio, média de avaliação, tarefas
  concluídas, mensagem e valor proposto — antes de escolher. Ao escolher,
  a tarefa vai para "em andamento", o valor proposto vira o combinado e os
  demais candidatos são recusados.
- **Avaliações:** ao concluir, o contratante avalia o prestador (1 a 5
  estrelas + comentário opcional), uma única vez por tarefa. A média do
  prestador é recalculada na hora.
- **Dashboard:** painel do contratante (tarefas por status, candidatos
  pendentes, avaliações pendentes como próximo passo) e painel do prestador
  (candidaturas enviadas, aceitas, concluídas), com abas quando o usuário
  tem os dois papéis.
- **Assistente de IA:** no formulário de criação de tarefa, o contratante
  pode descrever o pedido em linguagem natural (ex.: *"preciso lavar meu
  carro sábado, pago 50 reais"*) e a IA preenche título, descrição,
  categoria e valor sugerido automaticamente. Se a API falhar ou a chave
  não estiver configurada, o formulário continua utilizável normalmente
  (preenchimento manual).
- **Experiência mobile:** menu hambúrguer acessível, áreas de toque de 44px+,
  contraste revisado (laranja escurecido para textos e botões, WCAG AA).
- **Segurança:** `SECRET_KEY` obrigatória (o app não inicia sem ela), modo
  debug só com `FLASK_DEBUG=1`, autorização validada no servidor em todas
  as ações, páginas de erro consistentes (403, 404, 413, 500) e exclusão em
  cascata (sem candidaturas, mensagens, avaliações ou imagens órfãs).
- **Testes automatizados** (pytest): autenticação, permissões, candidatura,
  aceite, conclusão e avaliações.

### Fora do escopo desta entrega (roadmap futuro)

Para focar no fluxo principal (publicar → candidatar → escolher → concluir
→ avaliar), as seguintes funcionalidades ficam como próximos passos:

- **Próxima iteração (P1):** chat interno entre contratante e prestador
  escolhido (o model `Message` já existe e é apagado em cascata com a
  tarefa); upload seguro de até 3 imagens por tarefa (a coluna
  `image_filename` já existe); "salvar tarefa" e alertas internos por
  categoria/cidade para prestadores; painéis com histórico mais completo.
- **Fora do MVP (P2):** pagamentos, mapas e geolocalização em tempo real,
  verificação de documentos, notificações por e-mail/push/WhatsApp,
  recomendação avançada e painel administrativo.

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
10. Refinamento do MVP: avaliações, candidaturas comparáveis, agenda e
    localização estruturada, filtros/ordenação/paginação, menu mobile,
    reforço de segurança e testes automatizados

As etapas de **upload de imagens** e **mensagens** foram deliberadamente
escopadas para uma próxima iteração — o model `Message` e a coluna
`image_filename` já estão modelados no banco, prontos para receber a
implementação (ver seção *Fora do escopo desta entrega*).

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

- `SECRET_KEY` (**obrigatória** — o app não inicia sem ela): gere uma com
  `python -c "import secrets; print(secrets.token_hex(32))"`.
- `FLASK_DEBUG`: use `1` só na sua máquina, durante o desenvolvimento.
- `OPENAI_API_KEY`: opcional. Sem ela, o assistente de IA mostra um aviso e
  o formulário de criação de tarefa continua funcionando normalmente
  (preenchimento manual).

### 4. Banco de dados

```bash
flask db upgrade
```

Isso cria `ajudala.db` na raiz do projeto com todas as tabelas — ou, num
banco já existente, aplica as migrations novas preservando os dados (a
migration de localização converte o antigo campo "Bairro, Cidade" em
cidade e bairro separados).

### 5. Dados de demonstração (opcional, recomendado)

```bash
python seed.py
```

Cria 4 contas de demonstração, todas com senha `senha123`:

| E-mail | Papel |
|---|---|
| `mariana@example.com` | Contratante (tarefa com 3 candidatos para comparar e 1 avaliação pendente) |
| `joao@example.com` | Prestador com histórico (2 avaliações, média 4,5) |
| `rafael@example.com` | Prestador novo |
| `carla@example.com` | Contratante **e** prestadora |

E popula 9 tarefas em todos os status (abertas, em andamento, concluídas)
para que o fluxo completo já apareça pronto ao navegar pelo site.

> **Atenção:** `seed.py` apaga e recria todas as tabelas. Não rode em um
> banco com cadastros reais que você queira manter.

### 6. Rodar o servidor

```bash
python app.py
```

Acesse `http://localhost:5000`.

### 7. Testes automatizados

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Cada teste roda num banco SQLite em memória, isolado do `ajudala.db`.

### 8. Gerar o pacote de entrega

```bash
git archive --format=zip -o ajuda-la-entrega.zip HEAD
```

O `git archive` empacota só o que está versionado: `.git`, `venv/`, `.env` e
o banco local ficam de fora automaticamente (veja `.gitignore`).

## Estrutura do projeto

```
ajuda-la/
├── app.py                  # Application factory, registro de blueprints
├── config.py                # Configurações (lidas do .env)
├── extensions.py             # db, migrate, login_manager
├── utils.py                  # CSRF manual, moeda, datas, tempo relativo, ícones
├── seed.py                   # Dados de demonstração
├── models/                   # User, Task, Application, Message, Review
├── routes/                   # Blueprints: auth, profile, tasks, applications, reviews, dashboard, ai
├── tests/                    # Testes automatizados (pytest)
├── services/
│   └── ai_service.py         # Integração com a OpenAI API
├── templates/                # Jinja2, organizados por blueprint
├── static/
│   ├── css/style.css         # Design system (paleta, componentes)
│   ├── js/                   # ai-assistant.js, main.js
│   └── img/logo.png
└── migrations/                # Histórico de migrations (Flask-Migrate)
```


