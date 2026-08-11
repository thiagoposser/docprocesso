# Análise arquitetural da evolução do DocProcesso

## 1. Objetivo e limites

Este documento descreve a evolução incremental do DocProcesso para tramitação administrativa, sem implementar funcionalidades. A análise parte do código existente na `main` após a DP-001 e preserva autenticação JWT, usuários, layout Angular, APIs existentes, PostgreSQL, Redis, Docker Compose, Nginx, auditoria, notificações e armazenamento de mídia.

Não se recomenda reescrever módulos existentes, alterar infraestrutura, trocar autenticação ou introduzir novas tecnologias antes de necessidade comprovada.

## 2. Estado atual

### 2.1 Estrutura e infraestrutura

- Backend Django 6 e Django REST Framework organizado em apps sob `backend/apps/`: `core`, `users`, `documents`, `audit` e `notifications`.
- Frontend Angular 22 standalone, com rotas lazy-loaded, serviços HTTP em `core`/`features`, Signals, Reactive Forms e Bootstrap 5.
- PostgreSQL é o banco principal. Redis está provisionado e persistente, mas ainda não participa de uma regra funcional.
- Nginx integra Angular e Django; PgAdmin é ferramenta operacional.
- Docker Compose é a referência de desenvolvimento. Código de backend e frontend usa bind mount; mídia usa volume persistente.
- Produção já possui overrides para Gunicorn, build estático Angular e mídia/estáticos via Nginx.

### 2.2 Funcionalidades existentes e reutilizáveis

| Área | O que existe | Como reutilizar |
|---|---|---|
| Autenticação | Usuário customizado compatível com `AbstractUser`, JWT, rotação/blacklist, login, refresh, logout e `/me` | Manter integralmente; ampliar somente dados retornados quando o vínculo setorial exigir |
| Autorização | Groups, Permissions, `IsAdministrator`, guards Angular e permissões retornadas no usuário atual | Criar permissões Django por capacidade e combinar com escopo setorial no backend |
| Usuários | CRUD administrativo, grupos, permissões diretas, foto, filtros e auditoria | Complementar com vínculo N:N a setores; não alterar `AUTH_USER_MODEL` |
| Documentos | Categoria configurável, documento com arquivo ou URL, validação de extensão/MIME/tamanho, download autorizado, filtros e tela CRUD | Evoluir para documento lógico e anexos, preservando registros e endpoints durante transição |
| Auditoria | `AuditLog` read-only, snapshots sanitizados, ator, IP, rota, ação, entidade e filtros | Manter como trilha transversal de segurança; não usá-lo como único histórico de tramitação |
| Notificações | Notificação interna por usuário, contador, leitura, expiração e service central | Adicionar novos tipos/eventos depois que processos e pagamentos estiverem estáveis |
| Configurações | Singleton público/administrativo, manutenção, identidade e logo | Preservar; eventualmente hospedar parâmetros públicos, não estados de workflow nem segredos |
| Dashboard | Endpoint e tela com usuários, documentos, saúde, ambiente e auditoria recente | Ampliar contratos e cards sem substituir o dashboard existente |
| Testes | 24 testes backend em `APITestCase`; autenticação, documentos, auditoria, notificações e configurações | Seguir o padrão Django/DRF; não há testes Angular nem Cypress/Playwright instalados |

### 2.3 Endpoints atuais a preservar

- Autenticação: `/api/auth/login/`, `/api/auth/refresh/`, `/api/auth/logout/`, `/api/auth/me/`.
- Usuários: `/api/users/` e `/api/users/{id}/`.
- Documentos: `/api/documents/`, `/api/documents/{id}/`, `/api/documents/{id}/download/` e `/api/document-categories/`.
- Operação: `/api/health/`, `/api/dashboard/`, `/api/settings/public/` e `/api/settings/`.
- Auditoria e notificações: `/api/audit-logs/`, `/api/notifications/` e ações existentes.

Compatibilidade desses contratos deve ser tratada explicitamente nas migrations e nas tarefas de evolução documental.

### 2.4 Lacunas

Não existem atualmente: setores hierárquicos; vínculo usuário-setor; processo administrativo; número de processo; estados de processo; tramitação; recebimento; devolução; conclusão/reabertura; histórico de domínio; documento associado a processo; múltiplos anexos por documento; fornecedor; pagamento; vencimento; comprovante; escopo setorial; relatórios de domínio; busca de processos; indicadores financeiros; controle de concorrência por versão/lock.

## 3. Arquitetura recomendada

### 3.1 Apps Django

Manter os apps atuais e adicionar somente:

- `apps.sectors`: `Sector` e `UserSectorMembership`, hierarquia e políticas de abrangência.
- `apps.processes`: `AdministrativeProcess`, `ProcessMovement` e `ProcessEvent`, regras de estado e serviços transacionais.
- `apps.payments`: `Supplier` e `Payment`, regras financeiras e consultas de vencimento.

O app `documents` permanece responsável por `DocumentCategory`, documento lógico, anexos, validação e acesso a arquivo. `audit` continua transversal. Essa separação evita um app monolítico e também evita reorganizar o que funciona.

### 3.2 Entidades propostas

| Entidade | Responsabilidade e campos centrais |
|---|---|
| `Sector` | Estrutura flexível pai/filho: nome, sigla/código opcional, `parent`, responsável opcional, ativo, timestamps. Impedir ciclos e pai inativo em novos vínculos. |
| `UserSectorMembership` | Vínculo explícito N:N entre usuário e setor: ativo, principal, responsável, início/fim opcional. Permite múltiplos setores e futura delegação sem sobrecarregar Groups. |
| `AdministrativeProcess` | Número único, título, descrição, tipo/categoria configurável, criador, setor de origem, setor atual, responsável opcional, estado, versão, datas de abertura/conclusão/arquivamento e flags de integridade. |
| `ProcessMovement` | Registro imutável de tramitação: processo, ação, origem, destino, ator, observação, estado anterior/posterior, criado em. Representa fatos de encaminhar, receber, devolver, finalizar, reabrir, cancelar e arquivar. |
| `ProcessEvent` | Histórico imutável de fatos relevantes que não são tramitação, com ação, ator, descrição e snapshots mínimos. Referencia o processo e opcionalmente documento/pagamento por identificadores explícitos. |
| `DocumentCategory` | Tipo documental configurável já existente. Pode ganhar metadados comportamentais mínimos, sem transformar regras críticas em configuração arbitrária. |
| `Document` | Documento lógico, independente ou pertencente a um processo; mantém título, descrição, categoria, autoria, ativo e timestamps. Durante migração, preserva arquivo/URL legado. |
| `Attachment` | Um arquivo ou URL por registro, pertencente a documento: nome original, arquivo/URL, MIME declarado/validado, tamanho, autor, ativo/removido logicamente e timestamps. |
| `Supplier` | Fornecedor normalizado: nome/razão social, CPF/CNPJ normalizado e opcional, ativo. Evita repetir identidade em pagamentos, sem armazenar dados bancários permanentes. |
| `Payment` | Pertence a processo e opcionalmente a documento fiscal; fornecedor, número da nota, emissão, finalidade, setor da despesa, valores previsto/pago, vencimento, forma, status persistido, dados de instrução estritamente necessários, responsáveis e timestamps. |

### 3.3 Relações principais

```text
User 1 ── N UserSectorMembership N ── 1 Sector
Sector 1 ── N Sector (parent/children)

AdministrativeProcess N ── 1 Sector (origin/current)
AdministrativeProcess 1 ── N ProcessMovement
AdministrativeProcess 1 ── N ProcessEvent
AdministrativeProcess 1 ── N Document
Document 1 ── N Attachment

AdministrativeProcess 1 ── N Payment
Payment N ── 0..1 Document
Payment N ── 0..1 Supplier
Payment 1 ── N Attachment (por documento de comprovante ou relação tipada definida na implementação)
```

Recomenda-se que comprovantes sejam documentos/anexos com categoria e finalidade explícitas, evitando um segundo mecanismo de upload. A decisão final entre `Payment.receipt_document` e um papel/tipo de vínculo deve ser tomada na tarefa de comprovantes, após validar a necessidade de múltiplos comprovantes.

## 4. Estados e ações

### 4.1 Processo

Estados de ciclo de vida devem começar como `TextChoices`, pois são poucos, governam transições e precisam de código/testes estáveis:

- `DRAFT`: ainda editável e não tramitado.
- `IN_PROGRESS`: em tramitação ou análise.
- `COMPLETED`: concluído, bloqueado para alterações comuns.
- `CANCELLED`: cancelado com motivo obrigatório.
- `ARCHIVED`: encerrado e arquivado; normalmente sucede conclusão/cancelamento.

“Recebido”, “encaminhado”, “devolvido”, “alterado” e “pago” são ações/eventos, não estados duradouros do processo. Se for necessário distinguir “aguardando recebimento” de “em análise”, isso deve ser modelado por situação operacional explícita ou pela última movimentação, após validação com usuários; não por dezenas de estados configuráveis.

Tipos de processo e documento devem ser entidades configuráveis. Estados e ações críticas não devem ser configuráveis inicialmente, pois permitir transições arbitrárias comprometeria regras, relatórios e auditoria. Fluxos configuráveis são evolução futura e só devem surgir após fluxos reais estabilizados.

### 4.2 Pagamento

Status persistidos recomendados:

- `PENDING`: existe obrigação e aguarda pagamento.
- `SCHEDULED`: pagamento agendado, ainda não confirmado.
- `PAID`: pagamento confirmado com data, valor e ator.
- `CANCELLED`: obrigação cancelada com motivo.

`OVERDUE` deve ser condição derivada (`status` pendente/agendado e vencimento anterior à data local), evitando inconsistência entre data e status. `SEM_PAGAMENTO` é ausência de `Payment`, não status. “Vence hoje” e “próximo do vencimento” também são filtros derivados.

## 5. Fluxo recomendado

1. Usuário com `processes.add_administrativeprocess` e vínculo ativo cria rascunho no setor de origem.
2. Inclusão de documentos/anexos respeita tipo, tamanho e acesso ao processo.
3. A abertura/encaminhamento inicial muda o processo para `IN_PROGRESS`, define o setor atual e cria movimento imutável.
4. O setor de destino recebe explicitamente quando a regra operacional exigir; recebimento registra ator e horário sem sobrescrever o encaminhamento.
5. Usuário autorizado analisa, complementa documentos e pode devolver ou encaminhar. Cada ação ocorre em service transacional.
6. Pagamento, quando aplicável, é cadastrado sem dados sensíveis desnecessários. Confirmação registra valor/data/forma/ator e comprovante segundo política.
7. Conclusão exige pré-condições (por exemplo, nenhum pagamento obrigatório pendente) e bloqueia edições comuns.
8. Reabertura, cancelamento e arquivamento exigem permissão específica e justificativa.

Toda ação crítica deve produzir, na mesma transação, mudança do agregado, movimento/evento de domínio e auditoria. Notificação pode ser criada na mesma transação inicialmente; integração assíncrona só será necessária se volume ou canais externos justificarem.

## 6. Regras de consistência e concorrência

- Serviços de ação usam `transaction.atomic()` e recarregam o processo com `select_for_update()` antes de validar estado/setor/versão.
- O cliente envia a versão conhecida (`version` inteiro ou `updated_at`), permitindo responder `409 Conflict` a edição obsoleta.
- Encaminhamento valida origem igual ao setor atual, destino ativo e diferente, vínculo/permissão do ator e transição permitida.
- Movimentos e eventos são append-only pela API; correção ocorre por evento compensatório, nunca por edição silenciosa.
- Confirmação de pagamento bloqueia a linha e é idempotente: pagamento já pago não pode ser confirmado novamente.
- Processos concluídos/cancelados/arquivados rejeitam alterações comuns; ações específicas podem reabrir ou arquivar.
- Constraints de banco garantem número único, valores não negativos, coerência básica de status/datas e unicidade de vínculo ativo/principal quando aplicável.
- Mudanças de setor e vínculo nunca removem histórico; inativação usa flags/datas. Soft delete só é aplicado onde exclusão administrativa teria impacto de rastreabilidade.

## 7. Autorização

Groups continuam representando perfis organizacionais configuráveis; Permissions representam capacidades. `UserSectorMembership` define onde a capacidade pode ser exercida.

Uma decisão de acesso deve combinar:

```text
usuário autenticado
AND permissão Django para a ação
AND vínculo/abrangência setorial compatível
AND estado do recurso permite a ação
```

Não se recomenda fixar quatro papéis no código. Grupos iniciais podem ser configurados administrativamente, mas checks devem usar codenames como `view_administrativeprocess`, `forward_administrativeprocess`, `receive_administrativeprocess`, `view_financial_data` e `confirm_payment`. Superusuário mantém bypass nativo. Guards Angular servem apenas à experiência; o backend é a autoridade.

## 8. Histórico versus auditoria

- `ProcessMovement`: verdade operacional da passagem entre setores e ações de fluxo.
- `ProcessEvent`: linha do tempo funcional do processo para fatos não representados por movimentação.
- `AuditLog`: trilha transversal de segurança e conformidade, incluindo request, IP e snapshots sanitizados.

Não duplicar payload completo. Movimento/evento guarda dados necessários para explicar o processo; auditoria guarda metadados técnicos e alterações sensíveis sanitizadas. A tela de processo combina movimentos e eventos em uma timeline; a tela administrativa de auditoria permanece separada.

## 9. Arquivos e segurança

- Reutilizar `MEDIA_ROOT`, volume `backend_media`, nomes UUID e download mediado pela API.
- Manter allowlist de extensão, tamanho e MIME; considerar inspeção de assinatura/magic bytes em tarefa própria.
- Nunca expor caminho físico nem confiar no nome/MIME enviados pelo navegador.
- Autorizar cada download conforme acesso ao processo, setor e dados financeiros.
- Remoção lógica do anexo mantém metadados e histórico. Exclusão física exige política de retenção separada e não deve ocorrer automaticamente.
- Linha digitável, chave PIX e dados bancários devem ser opcionais, mascarados nas respostas/listagens e excluídos de auditoria/logs quando considerados sensíveis. Não armazenar credenciais, tokens bancários, senha, CVV ou dados completos de cartão.

## 10. Busca, relatórios e dashboard

PostgreSQL atende o MVP com filtros indexados, `SearchVector`/trigram apenas se a busca textual simples se mostrar insuficiente. Começar com `icontains`/`SearchFilter` em campos selecionados, normalização de CPF/CNPJ e índices B-tree para número, status, setor, datas e vencimento.

Relatórios iniciais devem ser endpoints agregados com Django ORM, filtros validados e escopo de permissão. Não criar tabelas duplicadas, BI ou exportações assíncronas agora. Dashboard usa endpoints de resumo separados por domínio para não transformar `/api/dashboard/` em consulta monolítica cara.

Endpoints conceituais:

- `/api/dashboard/processes/`: contagens e tempos de tramitação visíveis ao usuário.
- `/api/dashboard/financial/`: totais e vencimentos, protegido por permissão financeira.
- `/api/reports/processes/` e `/api/reports/payments/`: agregações filtradas.
- `/api/search/`: busca unificada futura, ou inicialmente filtros nos próprios endpoints.

## 11. Frontend recomendado

Criar features lazy-loaded: `sectors`, `processes`, `payments` e `reports`. Reutilizar `PageHeader`, `StatusBadge`, `AppIcon`, layout, interceptador, autenticação, paginação e padrões de service/model. Usar Reactive Forms em novos formulários; o uso atual de `FormsModule` em filtros pode ser preservado.

Telas incrementais: árvore/lista de setores; vínculos do usuário; lista/formulário/detalhe de processos; timeline e ações; documentos/anexos dentro do processo; pagamentos pendentes/detalhe/registro; dashboard ampliado; relatórios com filtros.

Não adicionar biblioteca de árvore, estado global, gráficos ou testes E2E sem necessidade e autorização. Bootstrap/CSS e componentes simples bastam inicialmente.

## 12. Testes

- Backend: manter `django.test`/DRF `APITestCase`, apesar de o pedido citar pytest; pytest não está instalado e não deve ser introduzido sem decisão separada.
- Cobrir models/constraints, services transacionais, APIs, filtros, permissions e isolamento setorial.
- Testar concorrência em `TransactionTestCase` quando locks reais forem necessários.
- Frontend: o projeto possui script `ng test`, mas não contém specs. Cada feature deve incluir testes unitários Angular de services, guards e regras de formulário.
- Cypress/Playwright não estão presentes; não adicionar no backlog obrigatório do MVP.

## 13. Riscos de regressão

1. Transformar o `Document` existente pode quebrar arquivos, endpoints e telas; exige migration aditiva e compatibilidade temporária.
2. Filtragem setorial incorreta pode expor processos, comprovantes ou valores financeiros.
3. Atualizações sem lock podem perder encaminhamentos ou duplicar pagamentos.
4. Estados redundantes podem divergir de datas/eventos, especialmente “vencido”.
5. Auditoria excessiva pode armazenar dados financeiros sensíveis; auditoria insuficiente prejudica rastreabilidade.
6. Consultas hierárquicas ingênuas e timelines sem índices podem degradar com volume.
7. Alterar grupos padrão ou guards existentes pode bloquear usuários atuais.
8. Exclusão física ou migrations destrutivas podem perder documentos e dados persistidos.

## 14. Áreas que não devem ser alteradas sem necessidade comprovada

- Estratégia JWT, `AUTH_USER_MODEL`, tokens, guards e interceptor existentes.
- Dockerfiles, Compose, Nginx, portas, volumes PostgreSQL/Redis/mídia.
- Migrations históricas e dados atuais.
- Configurações globais, tema Bootstrap, layout, rotas e endpoints existentes.
- Auditoria e notificações atuais, exceto extensões pontuais por novos eventos.
- Dependências e versões principais.

O backlog detalhado e sua ordem de execução estão em `docs/DOCPROCESSO_WORKFLOW_BACKLOG.md`.
