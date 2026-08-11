# DocProcesso

Aplicação para gestão de processos e documentos, construída sobre uma base reutilizável com Angular 22, Django REST Framework, PostgreSQL, Redis, PgAdmin e Nginx. Nenhuma dependência global de Python, Node ou Angular é necessária: o fluxo completo usa Docker Compose.

## Arquitetura e estrutura

```text
backend/                    Código e configuração Django
frontend/                   Aplicação Angular
docker/backend/             Imagem e entrada do Django
docker/frontend/            Imagem Angular (dev e produção)
docker/postgres/            Inicialização do banco
docker/nginx/               Proxy reverso de dev e produção
docker/redis/               Configuração de persistência Redis
docker/pgadmin/             Cadastro automático do servidor PostgreSQL
scripts/                    Inicialização e atualização do template
docs/                       Decisões de arquitetura
docker-compose.yml          Ambiente de desenvolvimento
docker-compose.prod.yml     Sobrescritas para produção
```

O Nginx é o ponto de entrada integrado: encaminha `/api/` e `/admin/` ao Django e as demais rotas ao Angular. Consulte `docs/ARCHITECTURE.md` para as convenções de crescimento.

## Pré-requisitos e instalação

Instale apenas Docker Desktop (Windows, com WSL 2) ou Docker Engine com o plugin Compose (Linux). Este template já inclui um `.env` local para o primeiro uso. Em um clone futuro, crie-o a partir do exemplo antes de iniciar:

```bash
cp .env.example .env
docker compose up --build
```

No PowerShell, use `Copy-Item .env.example .env`. Troque todos os valores `change-me` antes de compartilhar ou publicar o ambiente. Na primeira execução, Compose baixa as imagens, instala dependências dentro delas, inicializa o banco e aplica migrations.

## Configuração do ambiente

O `.env.example` é o modelo versionado: documenta todas as variáveis necessárias e contém somente valores seguros para desenvolvimento. O `.env` é a configuração local efetivamente lida pelo Docker Compose e pelos containers; ele pode conter segredos e está bloqueado pelo `.gitignore`.

As portas publicadas podem ser alteradas no `.env` sem editar o Compose:

```dotenv
ANGULAR_PORT=4300
DJANGO_PORT=8100
NGINX_PORT=8180
PGADMIN_PORT=5150
```

Para alterar o banco, mantenha `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` e `DATABASE_URL` sincronizados. Por exemplo:

```dotenv
POSTGRES_DB=meu_banco
POSTGRES_USER=meu_usuario
POSTGRES_PASSWORD=uma-senha-forte
DATABASE_URL=postgresql://meu_usuario:uma-senha-forte@postgres:5432/meu_banco
```

O PostgreSQL aplica usuário, senha e script inicial somente ao criar o volume. Se o volume já possuir dados, altere as credenciais dentro do banco ou, apenas se puder perder os dados locais, execute `docker compose down --volumes` antes de recriá-lo.

O login inicial do PgAdmin é controlado por `PGADMIN_DEFAULT_EMAIL` e `PGADMIN_DEFAULT_PASSWORD`. Assim como no PostgreSQL, esses valores inicializam um volume novo; alterar o `.env` não substitui automaticamente uma conta já persistida.

## Endereços de desenvolvimento

| Serviço | Endereço/porta | Observação |
|---|---|---|
| Aplicação via Nginx | http://localhost:8180 | Entrada recomendada |
| Angular direto | http://localhost:4300 | Servidor com hot reload |
| Django API | http://localhost:8100/api/health/ | Health check público |
| Django admin | http://localhost:8100/admin/ | Crie um superusuário |
| PgAdmin | http://localhost:5150 | Credenciais do `.env` |
| PostgreSQL | `docker compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"` | Porta interna 5432, não publicada por segurança |
| Redis | `docker compose exec redis redis-cli` | Porta interna 6379, não publicada por segurança |

O servidor PostgreSQL aparece automaticamente no PgAdmin como **PostgreSQL (Docker)**. Na primeira conexão, informe `POSTGRES_PASSWORD` do `.env`; o cadastro automático não grava a senha em um arquivo versionado.

Se uma ferramenta do host precisar de conexão direta, adicione temporariamente `ports: ["5433:5432"]` ao serviço PostgreSQL (ou `6380:6379` ao Redis) em um arquivo Compose local não versionado.

## Comandos úteis

```bash
# Executar comandos Django
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate

# Logs e encerramento
docker compose logs -f backend frontend
docker compose down

# Remover também dados persistentes (ação destrutiva)
docker compose down --volumes
```

Os volumes bind de `backend/` e `frontend/` habilitam hot reload. `node_modules` fica em volume nomeado para evitar incompatibilidades entre Windows/Linux e o Linux do container.

## Autenticação e administração de usuários

Crie a primeira conta administrativa sem instalar Python no host:

```bash
docker compose exec backend python manage.py createsuperuser
```

Entre em `http://localhost:4300/login`. A API usa JWT com access token de curta duração, renovação automática por refresh token e blacklist no logout. Os tokens ficam em `sessionStorage`, portanto a sessão não é compartilhada entre abas nem mantida depois de fechar a aba.

Os grupos **Administrador** e **Usuário** são criados automaticamente depois das migrations. Superusuários, membros da equipe e integrantes de **Administrador** podem acessar `/administracao/usuarios`, criar contas e alterar dados, status e grupos. A senha nunca é retornada pela API. Permissões detalhadas podem ser atribuídas pelo Django Admin.

Endpoints principais:

| Método | Endpoint | Finalidade |
|---|---|---|
| `POST` | `/api/auth/login/` | Obter tokens e dados da conta |
| `POST` | `/api/auth/refresh/` | Renovar o access token |
| `POST` | `/api/auth/logout/` | Invalidar o refresh token |
| `GET` | `/api/auth/me/` | Consultar a conta autenticada |
| `GET` | `/api/dashboard/` | Resumo real do ambiente |
| `GET/POST` | `/api/users/` | Listar ou criar usuários (admin) |
| `GET/PATCH` | `/api/users/{id}/` | Consultar ou editar usuário (admin) |

As rotas Angular internas exigem autenticação; a área administrativa exige perfil administrativo. Respostas `401` tentam renovar a sessão uma vez e respostas sem autorização direcionam para `/403`.

## Módulo de documentos

Usuários autenticados consultam documentos ativos em `http://localhost:4300/documentos`. Administradores podem cadastrar, editar, ativar e desativar documentos, além de criar categorias no próprio formulário. A interface não realiza exclusão física.

Cada documento possui exatamente uma origem: arquivo enviado ou URL externa HTTP/HTTPS. Por padrão, são aceitos `pdf`, `doc`, `docx`, `xls`, `xlsx`, `txt`, `png`, `jpg` e `jpeg`, com limite de 10 MB. Ajuste `DOCUMENT_ALLOWED_EXTENSIONS` e `DOCUMENT_MAX_UPLOAD_MB` no `.env` para outro projeto.

Uploads recebem nomes UUID e são armazenados no volume Docker `backend_media`, montado em `MEDIA_ROOT`; portanto não ficam no código-fonte. O nome original é guardado apenas como metadado para exibição. Em produção, o volume serve como base inicial, mas armazenamento de objetos, antivírus e URLs assinadas são recomendados conforme o risco da aplicação.

Endpoints do módulo:

| Método | Endpoint | Acesso |
|---|---|---|
| `GET` | `/api/documents/` | Usuário autenticado |
| `POST` | `/api/documents/` | Administrador |
| `GET` | `/api/documents/{id}/` | Usuário autenticado; apenas ativos para usuário comum |
| `PATCH` | `/api/documents/{id}/` | Administrador |
| `GET` | `/api/document-categories/` | Usuário autenticado |
| `POST/PATCH` | `/api/document-categories/` e `/api/document-categories/{id}/` | Administrador |

## Configurações do sistema

A tela administrativa `http://localhost:4300/configuracoes` centraliza nome, nome curto, descrição, versão, logo, cor principal, localização, suporte e modo de manutenção. Essas informações ficam em um registro singleton no PostgreSQL. Segredos, credenciais e URLs internas continuam exclusivamente no `.env`.

O frontend consulta `GET /api/settings/public/` durante sua inicialização e aplica nome, logo, idioma, título do navegador e cor principal. Esse endpoint usa uma lista explícita de campos públicos. `GET/PATCH /api/settings/` exige perfil administrativo e inclui as demais configurações não sensíveis.

Quando o modo de manutenção está ativo, requisições comuns recebem HTTP `503` com o código `maintenance_mode`, e o Angular direciona para `/manutencao`. Health check, configurações públicas e endpoints necessários para autenticação permanecem disponíveis. Administradores autenticados continuam com acesso normal.

A logo aceita PNG, JPG/JPEG ou WEBP com até 2 MB e utiliza o mesmo volume persistente de mídia dos documentos. SVG não é aceito para evitar conteúdo ativo no mesmo domínio da aplicação.

## Auditoria e logging

A auditoria funcional registra criações e alterações de usuários, grupos e permissões, criação/edição/ativação/desativação/visualização/download de documentos, alterações das configurações, login, falha de login e logout. Usuários com `audit.view_auditlog` consultam os registros em `/administracao/auditoria` ou pela API read-only `/api/audit-logs/`.

Os snapshots usam listas explícitas de campos e um sanitizador recursivo remove chaves relacionadas a senhas, tokens, secrets, autorização, cookies e credenciais. Conteúdo de arquivos e headers sensíveis não são persistidos. Os registros possuem índices de data, ação, usuário, entidade e ID da entidade.

Logs técnicos permanecem separados no `LOGGING` do Django e são enviados ao console do container. Ajuste `LOG_LEVEL` no `.env`; desenvolvimento usa formato legível e produção usa formato consistente para coletores. Exceções não geram `AuditLog` automaticamente.

Nenhuma retenção automática é aplicada. Antes de operar em produção, defina uma política compatível com requisitos legais e de armazenamento, por exemplo 90, 180 ou 365 dias, com arquivamento antes da exclusão quando necessário.

## Notificações internas

Cada usuário consulta apenas suas próprias notificações pelo sino do header ou por `/notificacoes`. O badge usa `/api/notifications/unread-count/`; leitura individual e leitura em lote atualizam imediatamente o estado global baseado em Signals.

Toda criação passa por `NotificationService`, que também oferece operações preparadas para listas de usuários e grupos. Nesta etapa, uma conta nova avisa o próprio usuário, documento criado avisa o autor, documento alterado por outra pessoa avisa o responsável e alteração das configurações avisa os demais administradores.

`action_url` aceita apenas caminhos internos iniciados por `/` (mas não `//`) ou URLs absolutas HTTP/HTTPS. Notificações expiradas deixam de aparecer e de entrar no contador, mas não são apagadas automaticamente. WebSocket, e-mail, SMS, push, Celery e Channels não fazem parte desta etapa; o service centralizado é o ponto de extensão para canais futuros.

## Produção

O arquivo de produção troca `ng serve` por arquivos Angular estáticos, `runserver` por Gunicorn, remove portas diretas de banco/cache e deixa PgAdmin desativado por padrão:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Para produção, altere no `.env` pelo menos `ENVIRONMENT=production`, `DEBUG=False`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `SECRET_KEY`, hosts, origens e todas as credenciais. Para habilitar PgAdmin temporariamente, acrescente `--profile tools`. Antes de uma implantação real, configure TLS no proxy/ingress, secrets externos, backup do PostgreSQL, observabilidade e réplicas conforme a plataforma.

## Reutilizando o template

Em uma cópia limpa, personalize os identificadores iniciais sem instalar Python adicional no host. O exemplo funciona em shells POSIX; no PowerShell, `${PWD}` também é resolvido pelo Docker Desktop:

```bash
docker run --rm -v "${PWD}:/workspace" -w /workspace python:3.14.5-slim-trixie python scripts/init-project.py "Meu Projeto"
```

O script está preparado com uma tabela central de substituições e `--dry-run`; futuras evoluções podem acrescentar nome de app, pacote Django, título Angular e geração de segredos. Para manutenção rotineira, execute `scripts/update.sh` (Linux/macOS) ou `scripts/update.ps1` (Windows).

## Licença

Distribuído sob a licença MIT. Veja `LICENSE`.
