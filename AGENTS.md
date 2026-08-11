# AGENTS.md

## OBJETIVO DO PROJETO

Este repositório é um template base reutilizável para aplicações Angular + Django.

A infraestrutura atual está funcional e deve ser preservada.

O agente deve sempre priorizar:

1. estabilidade;
2. compatibilidade;
3. reutilização;
4. segurança;
5. alterações mínimas;
6. preservação do que já funciona.

---

# REGRA PRINCIPAL

NÃO altere, remova, recrie ou reorganize partes do projeto que não sejam necessárias para a tarefa solicitada.

Se uma tarefa disser "alterar frontend", não modificar backend.

Se disser "alterar documentos", não modificar autenticação, usuários, Docker ou outras áreas sem necessidade comprovada.

Sempre fazer a menor alteração possível para cumprir a tarefa.

---

# ANTES DE QUALQUER ALTERAÇÃO

Antes de editar arquivos:

1. analisar a estrutura existente;
2. identificar quais arquivos realmente precisam ser modificados;
3. verificar dependências entre módulos;
4. preservar padrões existentes;
5. evitar refatorações não solicitadas.

Nunca usar uma tarefa pequena como oportunidade para refatorar o projeto inteiro.

---

# ALTERAÇÕES DESTRUTIVAS PROIBIDAS

Nunca executar sem autorização explícita:

docker compose down -v

docker volume rm

docker system prune

docker system prune -a

docker volume prune

DROP DATABASE

DROP TABLE

TRUNCATE

flush

reset de banco

remoção de migrations

recriação completa de migrations

remoção de volumes PostgreSQL

remoção de volumes Redis

remoção de node_modules sem necessidade

remoção de arquivos de configuração existentes

rm -rf em diretórios importantes

Nunca apagar dados persistentes.

---

# BANCO DE DADOS

O PostgreSQL contém dados que devem ser preservados.

Nunca:

- apagar volumes;
- recriar banco;
- resetar banco;
- executar migrations destrutivas sem avisar;
- remover migrations existentes;
- alterar tipos de campos de forma destrutiva sem análise.

Antes de uma migration potencialmente destrutiva:

PARAR.

Informar:
- qual alteração será feita;
- qual o risco;
- quais dados podem ser afetados;
- qual estratégia segura será usada.

Somente prosseguir após autorização explícita.

---

# DJANGO

Preservar:

backend/
config/
apps/
migrations/
settings existentes
URLs existentes
permissões existentes
autenticação existente

Não substituir configurações Django inteiras quando uma alteração pontual resolver.

Não alterar AUTH_USER_MODEL sem autorização explícita.

Não remover apps instalados sem autorização.

Não alterar estratégia de autenticação sem autorização.

Não modificar migrations antigas para resolver migrations novas.

Criar novas migrations quando necessário.

Sempre executar depois de alterações relevantes:

python manage.py check

E quando aplicável:

python manage.py test

---

# ANGULAR

Preservar:

frontend/
src/app/
core/
shared/
layouts/
features/
configuração Bootstrap
tema existente
rotas existentes
guards existentes
interceptors existentes
services existentes

Não recriar o projeto Angular.

Não executar ng new.

Não substituir angular.json sem necessidade.

Não trocar Bootstrap por outra biblioteca visual.

Não instalar:

Angular Material
PrimeNG
Tailwind
ng-bootstrap
ngx-bootstrap

sem autorização explícita.

Não alterar visual global quando a tarefa for específica de uma tela.

Não modificar todas as telas para resolver problema de apenas um componente.

Manter Angular standalone.

Usar lazy loading quando já for padrão do projeto.

Usar Reactive Forms nos formulários.

Não fazer chamadas HTTP diretamente em componentes quando já existir service apropriado.

Depois de alterações relevantes executar:

npm run build

---

# BOOTSTRAP E DESIGN

Bootstrap já faz parte do projeto.

Não remover Bootstrap.

Não substituir Bootstrap.

Preservar os tokens de tema e identidade visual existentes.

O design deve continuar:

- moderno;
- corporativo;
- minimalista;
- responsivo;
- acessível.

Não redesenhar componentes existentes sem solicitação explícita.

---

# DOCKER

A infraestrutura Docker atual funciona.

Preservar:

docker/
docker-compose.yml
docker-compose.prod.yml
Dockerfiles
Nginx
PostgreSQL
Redis
PgAdmin

Não alterar Docker por causa de uma funcionalidade comum de frontend/backend.

Alterar Docker somente quando realmente necessário.

Nunca mudar portas existentes sem autorização.

Portas atuais de desenvolvimento devem ser preservadas.

Não adicionar novos containers sem autorização explícita.

Nunca executar:

docker compose down -v

Para rebuild normal preferir:

docker compose up -d --build backend

ou:

docker compose up -d --build frontend

conforme o módulo alterado.

Não rebuildar todos os serviços quando apenas um precisa ser reconstruído.

---

# .ENV E SEGREDOS

Nunca colocar no código:

senhas
SECRET_KEY
tokens
credenciais de banco
credenciais SMTP
API keys

Preservar:

.env
.env.example

Nunca enviar conteúdo secreto do .env para documentação.

Nunca substituir o .env real automaticamente.

Ao adicionar uma variável:

1. adicionar ao .env.example;
2. documentar;
3. não sobrescrever o valor existente no .env sem necessidade.

---

# AUTENTICAÇÃO

Preservar toda a estratégia de autenticação existente.

Não trocar:

JWT
refresh token
cookies
guards
interceptors
permissions

sem solicitação explícita.

Nunca armazenar senha.

Nunca registrar senha em logs.

Nunca retornar senha pela API.

O backend é sempre a fonte final de autorização.

Não confiar apenas em guards do Angular.

---

# PERMISSÕES

Usar Django Groups e Permissions já existentes.

Não criar outro sistema paralelo de permissões.

Não alterar permissões existentes sem necessidade.

Não conceder acesso administrativo automaticamente.

---

# AUDITORIA

Preservar o sistema de auditoria.

Nunca registrar:

password
access token
refresh token
SECRET_KEY
cookies
Authorization header
credenciais de banco

Não apagar registros de auditoria sem autorização.

---

# DOCUMENTOS E ARQUIVOS

Não apagar arquivos enviados pelo usuário automaticamente.

Não alterar estrutura de MEDIA_ROOT sem necessidade.

Não remover documentos físicos ao apenas desativar registros.

Qualquer exclusão física deve exigir autorização explícita.

---

# CONFIGURAÇÕES DO SISTEMA

Não mover configurações sensíveis do .env para banco.

Configurações públicas podem ficar no banco.

Segredos continuam no ambiente.

Não alterar identidade visual global sem solicitação explícita.

---

# DEPENDÊNCIAS

Antes de instalar uma nova biblioteca:

1. verificar se a funcionalidade já pode ser feita com o que existe;
2. evitar dependência desnecessária;
3. preferir bibliotecas mantidas e estáveis;
4. explicar por que a dependência é necessária.

Não atualizar versões major automaticamente.

Não executar atualização geral de dependências sem solicitação.

Não usar:

npm update
npm audit fix --force
pip install --upgrade -r requirements.txt

indiscriminadamente.

---

# VERSÕES

Não atualizar automaticamente:

Angular
Node
Python
Django
PostgreSQL
Redis
Nginx
Bootstrap

Atualizações de versão devem ser tarefas separadas.

Antes de atualizar versão major:

1. informar versão atual;
2. informar versão proposta;
3. avaliar breaking changes;
4. criar plano;
5. aguardar autorização.

---

# ESCOPO DAS TAREFAS

Cada solicitação deve ter escopo limitado.

Exemplo:

Se a tarefa for:

"criar tela de grupos"

Pode alterar:

- arquivos relacionados a grupos;
- rotas necessárias;
- services necessários;
- permissões relacionadas;
- menu se necessário.

Não deve alterar:

- documentos;
- notificações;
- dashboard;
- Docker;
- tema;
- autenticação;

salvo necessidade técnica real.

---

# SE ENCONTRAR CÓDIGO RUIM

Não refatore automaticamente.

Informe:

"Encontrei uma possível melhoria em X, mas ela está fora do escopo desta tarefa."

Somente alterar se for necessário para cumprir o pedido ou se houver autorização.

---

# SE ENCONTRAR BUG FORA DO ESCOPO

Não corrigir silenciosamente.

Informar o problema.

Somente corrigir se:

- impedir a tarefa atual;
- representar risco grave;
- ou houver autorização.

---

# ARQUIVOS QUE EXIGEM CUIDADO EXTRA

Antes de modificar estes arquivos, confirmar que a alteração é realmente necessária:

docker-compose.yml
docker-compose.prod.yml
.env
.env.example
backend/config/settings/*
backend/config/urls.py
frontend/angular.json
frontend/package.json
frontend/package-lock.json
frontend/src/styles/*
docker/*
nginx/*
migrations existentes

Evitar substituir esses arquivos inteiros.

Preferir alterações pontuais.

---

# COMANDOS

É permitido executar comandos seguros de validação, como:

docker compose config
docker compose ps
docker compose logs
python manage.py check
python manage.py test
npm run build

Comandos que alteram ou removem dados precisam de autorização.

---

# TESTES

Após uma alteração, testar somente o necessário.

Frontend:

npm run build

Backend:

python manage.py check
python manage.py test

Docker:

docker compose config

Se precisar reconstruir:

docker compose up -d --build frontend

ou:

docker compose up -d --build backend

Não reiniciar banco, Redis ou demais serviços sem necessidade.

---

## Ambiente de desenvolvimento

O projeto é executado prioritariamente via Docker Compose.

Não assuma que Node.js, Angular CLI, Python, PostgreSQL, Redis ou dependências da aplicação estejam instalados no host.

Antes de executar validações:

1. consulte o arquivo Docker Compose;
2. identifique os nomes reais dos serviços;
3. verifique os containers com `docker compose ps`;
4. execute comandos de aplicação dentro dos containers correspondentes.

Exemplos:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py test
docker compose exec frontend npm run build
```

---

# RELATÓRIO FINAL

Ao terminar uma tarefa, sempre informar:

1. arquivos criados;
2. arquivos alterados;
3. migrations criadas;
4. dependências adicionadas;
5. endpoints criados/alterados;
6. rotas Angular criadas/alteradas;
7. testes executados;
8. containers rebuildados;
9. pendências;
10. qualquer alteração fora do escopo originalmente solicitado.

---

# PROIBIDO FAZER AUTOMATICAMENTE

Não fazer automaticamente:

- commit;
- push;
- merge;
- reset Git;
- apagar branch;
- publicação;
- deploy;
- alteração de produção;
- alteração de DNS;
- reset do banco;
- exclusão de dados;
- exclusão de volumes;
- atualização major de dependências.

Qualquer uma dessas ações exige autorização explícita.

---

# EM CASO DE DÚVIDA

Se houver dúvida entre:

A) alterar algo potencialmente importante

ou

B) perguntar antes

Escolher B.

Perguntar antes de executar qualquer alteração potencialmente destrutiva ou fora do escopo.

---

# PRINCÍPIO FINAL

O objetivo do agente é melhorar o projeto sem quebrar o que já funciona.

Preservar sempre:

- dados;
- infraestrutura;
- compatibilidade;
- autenticação;
- permissões;
- arquitetura;
- identidade visual;
- configurações.

Faça alterações pequenas, isoladas, testáveis e reversíveis.
