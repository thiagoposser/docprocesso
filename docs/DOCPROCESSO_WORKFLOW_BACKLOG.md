# Backlog de evolução do DocProcesso

## Convenções

- Continuidade da numeração: `DP-001` já identifica a adaptação de identidade; este backlog começa em `DP-002`.
- Endpoints estão propostos em inglês para manter o padrão atual (`documents`, `users`, `notifications`). Os rótulos da interface permanecem em português.
- Cada tarefa deve gerar migrations novas quando necessário; migrations existentes nunca devem ser editadas.
- Toda validação deve ocorrer no Docker Compose, sem presumir ferramentas instaladas no host.
- “Arquivos prováveis” indica áreas esperadas, não autorização para alterar todas elas.

## Fase 1 — Fundação organizacional e autorização

### DP-002 — Criar modelo hierárquico de setores

- **Objetivo:** adicionar `Sector` com nome, sigla/código, pai opcional, responsável opcional, ativo e timestamps.
- **Motivo:** processos, usuários, permissões, pagamentos e relatórios dependem de uma unidade organizacional consistente.
- **Dependências:** DP-001.
- **Backend envolvido:** novo app `apps.sectors`; model, admin e validação de ciclos.
- **Frontend envolvido:** nenhum nesta tarefa.
- **Banco envolvido:** nova tabela de setores, FK autorreferente `PROTECT`, índices em pai/ativo/nome e migration aditiva.
- **Endpoints previstos:** nenhum.
- **Regras de negócio:** hierarquia flexível; pai opcional; impedir autorreferência/ciclos; setor inativo não recebe novos processos/vínculos; inativação não remove histórico.
- **Permissões:** declarar `view/add/change_sector` e `manage_sector`; ainda sem API.
- **Critérios de aceite:** árvore arbitrária válida; ciclos rejeitados; registros não são apagados em cascata; migration preserva banco existente.
- **Testes necessários:** model, ciclos diretos/indiretos, inativação, `PROTECT` e constraints.
- **Riscos:** validação de ciclo com muitas queries; duplicidade de códigos.
- **Arquivos prováveis:** `backend/apps/sectors/*`, adição pontual em settings/admin.
- **Não alterar:** users, documents, autenticação, Docker e migrations antigas.
- **Complexidade:** média.

### DP-003 — Criar API administrativa de setores

- **Objetivo:** expor consulta hierárquica e CRUD sem exclusão física.
- **Motivo:** administrar a estrutura antes de vincular usuários e processos.
- **Dependências:** DP-002.
- **Backend envolvido:** serializers, viewset, permissions, service de hierarquia e URLs de `sectors`.
- **Frontend envolvido:** contratos apenas na tarefa posterior.
- **Banco envolvido:** consultas `select_related`; sem nova entidade além de eventual índice identificado.
- **Endpoints previstos:** `GET/POST /api/sectors/`, `GET/PATCH /api/sectors/{id}/`, `GET /api/sectors/tree/`.
- **Regras de negócio:** PATCH controla ativação; sem DELETE; resposta de árvore limitada e ordenada; pai deve estar ativo para nova alocação.
- **Permissões:** leitura autenticada conforme necessidade; escrita com `sectors.manage_sector`.
- **Critérios de aceite:** paginação/filtros, árvore correta, erros claros para ciclos e inativação inválida.
- **Testes necessários:** API, filtros, hierarquia, permissions, ausência de DELETE e query count básico.
- **Riscos:** payload recursivo excessivo e exposição de setores restritos no futuro.
- **Arquivos prováveis:** `backend/apps/sectors/{serializers,views,permissions,urls,tests}.py`, `backend/config/urls.py`.
- **Não alterar:** rotas/APIs existentes e infraestrutura.
- **Complexidade:** média.

### DP-004 — Criar tela de gestão de setores

- **Objetivo:** permitir listar, navegar na hierarquia, criar, editar, ativar e inativar setores.
- **Motivo:** disponibilizar a API organizacional para administradores.
- **Dependências:** DP-003.
- **Backend envolvido:** apenas correções contratuais comprovadas.
- **Frontend envolvido:** feature standalone lazy-loaded `sectors`, models, service, lista/árvore e formulário reativo.
- **Banco envolvido:** nenhum.
- **Endpoints previstos:** consumir endpoints da DP-003.
- **Regras de negócio:** impedir seleção do próprio nó/descendentes como pai; confirmar inativação; exibir responsável e estado.
- **Permissões:** rota/menu conforme `sectors.manage_sector`; backend permanece autoridade.
- **Critérios de aceite:** navegação responsiva/acessível, feedback de erros e hierarquia compreensível sem biblioteca nova.
- **Testes necessários:** service, formulário, renderização de árvore, visibilidade por permissão.
- **Riscos:** árvore profunda e UX em telas pequenas.
- **Arquivos prováveis:** `frontend/src/app/features/sectors/**`, `app.routes.ts`, `sidebar.ts`.
- **Não alterar:** tema global, layout, autenticação e Docker.
- **Complexidade:** média.

### DP-005 — Criar vínculo entre usuários e setores

- **Objetivo:** adicionar `UserSectorMembership` com setor, usuário, ativo, principal e indicador de responsável.
- **Motivo:** um usuário pode atuar em vários setores e as permissões precisam de escopo organizacional.
- **Dependências:** DP-002.
- **Backend envolvido:** model/service no app `sectors`; extensão aditiva dos serializers de usuário.
- **Frontend envolvido:** nenhum nesta tarefa.
- **Banco envolvido:** tabela associativa, unicidade usuário/setor, índices e regra de um vínculo principal ativo.
- **Endpoints previstos:** ampliar respostas `/api/auth/me/` e `/api/users/{id}/` somente após contrato versionado; CRUD dedicado na DP-006.
- **Regras de negócio:** vínculos são inativados, não excluídos; principal deve estar ativo; responsável não substitui Group/Permission; usuário/setor inativo não recebe novo vínculo.
- **Permissões:** declaração de `manage_user_sector_membership`.
- **Critérios de aceite:** múltiplos setores, um principal, histórico preservado e usuários atuais continuam válidos sem vínculo.
- **Testes necessários:** constraints, inativação, principal, compatibilidade dos usuários legados.
- **Riscos:** constraint parcial entre bancos; mudanças no payload de `/me`.
- **Arquivos prováveis:** `backend/apps/sectors/models.py`, migration nova, serializers e tests.
- **Não alterar:** `AUTH_USER_MODEL`, tabelas auth ou migrations de users.
- **Complexidade:** alta.

### DP-006 — Criar API e tela de vínculos usuário-setor

- **Objetivo:** administrar setores de cada usuário e expor seus vínculos ativos ao frontend.
- **Motivo:** tornar a alocação operacional e preparar autorização setorial.
- **Dependências:** DP-003, DP-005.
- **Backend envolvido:** serializer/viewset de memberships e extensão segura de `CurrentUserSerializer`.
- **Frontend envolvido:** interfaces e seção no formulário/detalhe de usuário.
- **Banco envolvido:** nenhuma nova tabela.
- **Endpoints previstos:** `GET/POST /api/user-sector-memberships/`, `GET/PATCH /api/user-sector-memberships/{id}/`; `/api/auth/me/` inclui setores ativos.
- **Regras de negócio:** alterações atômicas; impedir usuário sem setor principal quando política futura exigir, mas não impor no legado; auditar mudanças.
- **Permissões:** `sectors.manage_user_sector_membership` ou administração de usuários.
- **Critérios de aceite:** admin gerencia vínculos; usuário vê seus próprios setores; usuário comum não altera vínculos.
- **Testes necessários:** API, isolamento, payload `/me`, formulário Angular e regressão do CRUD de usuários.
- **Riscos:** N+1 em listagem de usuários e quebra de interfaces TypeScript.
- **Arquivos prováveis:** apps `sectors/users`, models Angular, user service/form.
- **Não alterar:** login/JWT, grupos padrão e interceptor.
- **Complexidade:** alta.

### DP-007 — Definir política reutilizável de acesso setorial

- **Objetivo:** implementar funções/classes que combinem Permission Django, membership ativo, setor e estado do recurso.
- **Motivo:** evitar checks divergentes e um sistema paralelo de papéis.
- **Dependências:** DP-005, DP-006.
- **Backend envolvido:** policies/permissions/services e codenames de domínio; documentação da matriz.
- **Frontend envolvido:** helper de capacidade baseado nas permissions já retornadas, apenas para UX.
- **Banco envolvido:** migrations de permissions dos models de domínio quando existirem.
- **Endpoints previstos:** nenhum novo; aplicação progressiva nos endpoints futuros.
- **Regras de negócio:** superusuário segue regra nativa; Group concede capacidade, membership concede escopo; negar por padrão; nunca confiar no guard Angular.
- **Permissões:** matriz para visualizar/criar/editar/encaminhar/receber/devolver/finalizar/reabrir, finanças, relatórios e setores.
- **Critérios de aceite:** policy testável sem request, mensagens consistentes e matriz aprovada.
- **Testes necessários:** combinações de grupo/permissão/setor, setor inativo, recurso fora do escopo e superusuário.
- **Riscos:** permissões amplas herdadas de grupos atuais.
- **Arquivos prováveis:** `backend/apps/sectors/policies.py`, permissions dos novos apps, auth models Angular.
- **Não alterar:** backend como fonte de autorização e estratégia auth.
- **Complexidade:** alta.

## Fase 2 — Processos, estados e tramitação

### DP-008 — Criar tipos e modelo base de processo administrativo

- **Objetivo:** adicionar tipo configurável e `AdministrativeProcess` com número único, dados descritivos, setores, responsáveis, estado e versão.
- **Motivo:** estabelecer o agregado central sem misturá-lo ao documento legado.
- **Dependências:** DP-002, DP-005, DP-007.
- **Backend envolvido:** novo app `processes`, models, admin e enums.
- **Frontend envolvido:** nenhum.
- **Banco envolvido:** tabelas de tipo/processo, FKs protegidas, constraints e índices em número/status/setor/datas.
- **Endpoints previstos:** nenhum.
- **Regras de negócio:** `TextChoices` para ciclo de vida; tipo configurável; número gerado de modo seguro; setor atual obrigatório fora de rascunho; sem exclusão física.
- **Permissões:** codenames nativos e customizados do processo.
- **Critérios de aceite:** criação de rascunho consistente, unicidade concorrente do número e transições não feitas por `save()` genérico.
- **Testes necessários:** model/constraints, geração de número, estados e proteção de FK.
- **Riscos:** formato do número e regra anual ainda requerem decisão de produto.
- **Arquivos prováveis:** `backend/apps/processes/{models,admin,apps,tests}.py`, migration e settings.
- **Não alterar:** `Document` nesta tarefa, auditoria e Docker.
- **Complexidade:** alta.

### DP-009 — Criar API CRUD e busca inicial de processos

- **Objetivo:** listar, criar, consultar e editar campos permitidos de processos.
- **Motivo:** disponibilizar o agregado antes das ações de tramitação.
- **Dependências:** DP-008.
- **Backend envolvido:** serializers separados para lista/detalhe/escrita, viewset, filters, permissions, URLs e service de criação.
- **Frontend envolvido:** contratos na tarefa seguinte.
- **Banco envolvido:** consultas e índices previstos na DP-008.
- **Endpoints previstos:** `GET/POST /api/processes/`, `GET/PATCH /api/processes/{id}/`, `GET /api/process-types/`.
- **Regras de negócio:** queryset sempre limitado por escopo setorial; PATCH não muda estado/setor atual diretamente; filtros por número, texto, tipo, status, setor, responsável e datas.
- **Permissões:** `view/add/change_administrativeprocess` combinadas com DP-007.
- **Critérios de aceite:** paginação, busca, filtros, 404 para recurso fora do escopo e contratos sem dados financeiros indevidos.
- **Testes necessários:** CRUD, filtros, permissions, isolamento setorial, tentativas de alterar campos protegidos.
- **Riscos:** vazamento por busca e serializers excessivos.
- **Arquivos prováveis:** `backend/apps/processes/{serializers,views,permissions,services,urls,tests}.py`, root URLs.
- **Não alterar:** endpoints existentes.
- **Complexidade:** alta.

### DP-010 — Criar telas básicas de processos

- **Objetivo:** implementar lista, criação, edição de rascunho e detalhe básico.
- **Motivo:** permitir uso do CRUD antes da timeline e ações avançadas.
- **Dependências:** DP-004, DP-006, DP-009.
- **Backend envolvido:** somente ajustes contratuais necessários.
- **Frontend envolvido:** feature `processes`, models, service, Reactive Forms, rotas lazy e menu.
- **Banco envolvido:** nenhum.
- **Endpoints previstos:** consumir DP-009 e catálogo de setores/tipos.
- **Regras de negócio:** ações visíveis por permissão/estado; tratamento de 403/404/409; filtros refletidos de forma previsível.
- **Permissões:** guards específicos de UX, sem substituir backend.
- **Critérios de aceite:** CRUD responsivo, paginação, acessibilidade, validação e preservação do layout.
- **Testes necessários:** services, formulário, filtros, estados de loading/erro e permissões visuais.
- **Riscos:** formulário crescer antes de documentos/pagamentos.
- **Arquivos prováveis:** `frontend/src/app/features/processes/**`, rotas/sidebar/icons.
- **Não alterar:** dashboard e documentos além de links necessários.
- **Complexidade:** alta.

### DP-011 — Criar modelo imutável de tramitação

- **Objetivo:** adicionar `ProcessMovement` append-only com ação, origem/destino, ator, observação e estados antes/depois.
- **Motivo:** manter rastreabilidade completa das movimentações.
- **Dependências:** DP-008.
- **Backend envolvido:** model/enums/admin read-only e manager/queryset.
- **Frontend envolvido:** nenhum.
- **Banco envolvido:** tabela de movimentos e índices por processo/data, origem/destino/ação.
- **Endpoints previstos:** nenhum de escrita genérica.
- **Regras de negócio:** registros não editáveis/deletáveis pela API; origem/destino coerentes por ação; observação obrigatória em devolução/cancelamento/reabertura.
- **Permissões:** `view_processmovement`; criação somente por services de ação.
- **Critérios de aceite:** sequência temporal íntegra e tentativas de mutação rejeitadas.
- **Testes necessários:** invariantes, ordenação, `PROTECT`, imutabilidade e índices declarados.
- **Riscos:** tentar representar toda alteração como movimento.
- **Arquivos prováveis:** models/migration/admin/tests do app `processes`.
- **Não alterar:** `AuditLog` para substituir tramitação.
- **Complexidade:** média.

### DP-012 — Implementar serviços transacionais de tramitação

- **Objetivo:** criar ações de abrir, encaminhar, receber, devolver, finalizar, reabrir, cancelar e arquivar.
- **Motivo:** centralizar regras e impedir atualizações concorrentes inconsistentes.
- **Dependências:** DP-007, DP-011.
- **Backend envolvido:** domain services com `transaction.atomic`, `select_for_update`, exceptions e eventos.
- **Frontend envolvido:** nenhum.
- **Banco envolvido:** locks nas linhas, incremento de versão e gravação atômica de movimentos.
- **Endpoints previstos:** nenhum nesta tarefa.
- **Regras de negócio:** matriz explícita de transições; destino ativo/diferente; ator com escopo; ações idempotentes quando aplicável; concluído/cancelado/arquivado bloqueia edição comum.
- **Permissões:** uma permission por ação sensível.
- **Critérios de aceite:** estado, setor, versão e movimento mudam juntos ou nada muda; conflito retorna erro de domínio mapeável para 409.
- **Testes necessários:** services, rollback, locks, transições inválidas, dupla ação e acesso fora do setor.
- **Riscos:** deadlocks e regras ainda não validadas com operação real.
- **Arquivos prováveis:** `backend/apps/processes/services/**`, tests.
- **Não alterar:** views para conter regra de negócio duplicada.
- **Complexidade:** alta.

### DP-013 — Expor ações e timeline de tramitação na API

- **Objetivo:** disponibilizar actions REST e consulta paginada da timeline.
- **Motivo:** permitir que o frontend use os services transacionais sem PATCH arbitrário.
- **Dependências:** DP-009, DP-012.
- **Backend envolvido:** action serializers, viewset actions, timeline serializer e permissions.
- **Frontend envolvido:** contratos na DP-014.
- **Banco envolvido:** nenhuma nova entidade.
- **Endpoints previstos:** `POST /api/processes/{id}/forward/`, `/receive/`, `/return/`, `/complete/`, `/reopen/`, `/cancel/`, `/archive/`; `GET /api/processes/{id}/timeline/`.
- **Regras de negócio:** payload mínimo, observação/motivo validado, versão obrigatória, resposta com processo atualizado.
- **Permissões:** codenames específicos e escopo setorial.
- **Critérios de aceite:** status HTTP coerentes (400/403/404/409), sem endpoint genérico para criar movimento.
- **Testes necessários:** cada action, timeline, permissions, concorrência simulada e serialização.
- **Riscos:** actions não idempotentes em retry de rede.
- **Arquivos prováveis:** views/serializers/urls/tests de `processes`.
- **Não alterar:** PATCH geral para burlar services.
- **Complexidade:** alta.

### DP-014 — Criar timeline e ações de tramitação no Angular

- **Objetivo:** mostrar histórico e permitir ações válidas no detalhe do processo.
- **Motivo:** completar o fluxo operacional entre setores.
- **Dependências:** DP-010, DP-013.
- **Backend envolvido:** nenhum salvo correções de contrato.
- **Frontend envolvido:** timeline, diálogos/formulários reativos, services de actions e atualização de Signals.
- **Banco envolvido:** nenhum.
- **Endpoints previstos:** consumir actions/timeline da DP-013.
- **Regras de negócio:** pedir confirmação/observação quando necessário; esconder/desabilitar ação inválida; tratar 409 recarregando dados sem perder texto do usuário.
- **Permissões:** capacidades retornadas ou permissions do usuário; backend valida novamente.
- **Critérios de aceite:** timeline clara com ator/data/origem/destino/estado e ações acessíveis/responsivas.
- **Testes necessários:** service, renderização, payloads, 409, visibilidade por estado/permissão.
- **Riscos:** inferir ações apenas no frontend e divergir do backend.
- **Arquivos prováveis:** feature `processes`, shared status/timeline se realmente reutilizável.
- **Não alterar:** layout/tema global.
- **Complexidade:** alta.

### DP-015 — Criar histórico funcional de processos e integrar auditoria

- **Objetivo:** registrar eventos não cobertos pela tramitação e ampliar `AuditAction` com ações de domínio.
- **Motivo:** explicar alterações de documentos, vencimentos e pagamentos sem duplicar movimentos.
- **Dependências:** DP-012, antes das integrações documental/financeira.
- **Backend envolvido:** `ProcessEvent`, service append-only e extensão pontual do audit service/actions.
- **Frontend envolvido:** timeline passa a combinar movimentos e eventos por contrato único.
- **Banco envolvido:** tabela de eventos com índices; payload JSON limitado e sanitizado.
- **Endpoints previstos:** timeline da DP-013 inclui eventos; sem criação pública genérica.
- **Regras de negócio:** evento criado pelo service que executa a ação; sem secrets/conteúdo de arquivos; correção por evento compensatório.
- **Permissões:** visualização acompanha acesso ao processo; auditoria administrativa mantém permissão própria.
- **Critérios de aceite:** fatos relevantes aparecem uma vez na timeline e também têm auditoria técnica quando aplicável.
- **Testes necessários:** sanitização, ordenação combinada, imutabilidade e ausência de duplicação.
- **Riscos:** crescimento de JSON e dados financeiros em logs.
- **Arquivos prováveis:** apps `processes/audit`, timeline Angular.
- **Não alterar:** registros antigos de auditoria.
- **Complexidade:** alta.

## Fase 3 — Documentos e anexos vinculados ao processo

### DP-016 — Evoluir documento para relação com processo e múltiplos anexos

- **Objetivo:** permitir documento independente ou associado a processo e criar `Attachment` 1:N.
- **Motivo:** o modelo atual mistura documento lógico com um único arquivo/URL.
- **Dependências:** DP-008, DP-015.
- **Backend envolvido:** models e estratégia de migração compatível no app `documents`.
- **Frontend envolvido:** nenhum nesta tarefa.
- **Banco envolvido:** FK opcional de processo, tabela de anexos e migration de dados em etapas; campos legados preservados até migração segura.
- **Endpoints previstos:** nenhum novo nesta tarefa.
- **Regras de negócio:** anexo tem exatamente arquivo ou URL; documento pode ter vários; remoção lógica; processo concluído bloqueia inclusão comum; categoria continua configurável.
- **Permissões:** acesso herdado do processo; documento independente segue política explícita.
- **Critérios de aceite:** documentos/arquivos existentes continuam acessíveis e novos anexos não duplicam metadados.
- **Testes necessários:** migration com dados legados, relações, validação de origem e regressão dos endpoints atuais.
- **Riscos:** maior risco de perda/regressão; requer backup e autorização antes da migration real.
- **Arquivos prováveis:** `documents/models.py`, migrations novas, serializers/tests.
- **Não alterar:** migrations existentes, MEDIA_ROOT e arquivos físicos.
- **Complexidade:** alta.

### DP-017 — Criar API segura de anexos e documentos do processo

- **Objetivo:** gerir documentos/anexos e downloads dentro do escopo do processo.
- **Motivo:** expor o novo modelo preservando compatibilidade do CRUD atual.
- **Dependências:** DP-007, DP-013, DP-016.
- **Backend envolvido:** serializers/viewsets/services/permissions de anexos; adaptação compatível de documents.
- **Frontend envolvido:** contratos na tarefa seguinte.
- **Banco envolvido:** consultas `select_related/prefetch_related`.
- **Endpoints previstos:** `GET/POST /api/processes/{id}/documents/`, `GET/PATCH /api/documents/{id}/`, `GET/POST /api/documents/{id}/attachments/`, `GET /api/attachments/{id}/download/`, `PATCH .../deactivate/`.
- **Regras de negócio:** download sempre autorizado; sem DELETE; upload validado no backend; ações geram evento/auditoria.
- **Permissões:** view/add/change document combinadas com processo/setor; comprovante requer permissão financeira.
- **Critérios de aceite:** isolamento setorial, múltiplos anexos, compatibilidade documentada e URLs físicas não expostas.
- **Testes necessários:** uploads, MIME/tamanho/nome, download, permissions, remoção lógica e regressão.
- **Riscos:** IDOR em download e substituição acidental de arquivo.
- **Arquivos prováveis:** app `documents`, integração `processes`, URLs/tests.
- **Não alterar:** armazenamento/volumes/Nginx.
- **Complexidade:** alta.

### DP-018 — Integrar documentos e anexos às telas de processo

- **Objetivo:** listar, anexar, visualizar e inativar documentos no detalhe do processo.
- **Motivo:** tornar o dossiê administrativo utilizável.
- **Dependências:** DP-014, DP-017.
- **Backend envolvido:** nenhum salvo ajustes de contrato.
- **Frontend envolvido:** componentes de documentos no processo, upload múltiplo sequencial/controlado e download seguro.
- **Banco envolvido:** nenhum.
- **Endpoints previstos:** consumir DP-017 e manter telas independentes atuais.
- **Regras de negócio:** validar UX de extensão/tamanho sem substituir validação backend; indicar anexo removido; respeitar estado/permissão.
- **Permissões:** controles por capabilities; backend obrigatório.
- **Critérios de aceite:** documentos independentes continuam funcionando e processo mostra seu dossiê/timeline.
- **Testes necessários:** service, formulário, downloads, erros parciais e permissões.
- **Riscos:** uploads grandes e inconsistência em múltiplos requests.
- **Arquivos prováveis:** features `processes/documents`, `documents` existentes apenas quando necessário.
- **Não alterar:** tema, storage ou endpoints sem compatibilidade.
- **Complexidade:** alta.

## Fase 4 — Pagamentos

### DP-019 — Criar modelos de fornecedor e pagamento

- **Objetivo:** modelar fornecedor e obrigação/pagamento ligados a processo, documento e setor.
- **Motivo:** suportar notas fiscais e controle financeiro sem sobrecarregar Document.
- **Dependências:** DP-008, DP-016.
- **Backend envolvido:** novo app `payments`, models, enums, validators e admin.
- **Frontend envolvido:** nenhum.
- **Banco envolvido:** tabelas, decimais, datas, FKs protegidas, constraints e índices de status/vencimento/setor/fornecedor.
- **Endpoints previstos:** nenhum.
- **Regras de negócio:** status `PENDING/SCHEDULED/PAID/CANCELLED`; vencido derivado; valores não negativos; pago exige data/valor/ator; CPF/CNPJ normalizado; dados bancários mínimos.
- **Permissões:** declarar view/add/change, `view_financial_data`, `confirm_payment`.
- **Critérios de aceite:** coerência status/datas/valores garantida e pagamento ausente representa “sem pagamento”.
- **Testes necessários:** model, constraints, precisão decimal, vencimento derivado e proteção de dados.
- **Riscos:** requisitos fiscais incompletos e armazenamento excessivo de dados bancários.
- **Arquivos prováveis:** `backend/apps/payments/**`, migration e settings/admin.
- **Não alterar:** Document para absorver todos os campos financeiros.
- **Complexidade:** alta.

### DP-020 — Criar API de fornecedores e pagamentos

- **Objetivo:** expor cadastro/consulta financeira, filtros e dados mascarados conforme permissão.
- **Motivo:** permitir gestão operacional antes da confirmação de pagamento.
- **Dependências:** DP-007, DP-019.
- **Backend envolvido:** serializers por contexto, viewsets, filters, policies, URLs e services.
- **Frontend envolvido:** contratos na DP-022.
- **Banco envolvido:** queries/indexes da DP-019.
- **Endpoints previstos:** `GET/POST /api/suppliers/`, `GET/PATCH /api/suppliers/{id}/`, `GET/POST /api/payments/`, `GET/PATCH /api/payments/{id}/`.
- **Regras de negócio:** filtros por período/setor/status/fornecedor/valor/vencimento; PATCH não confirma pagamento; campos sensíveis mascarados ou omitidos.
- **Permissões:** separar visualização de processo e dados financeiros; escopo pelo setor da despesa/processo.
- **Critérios de aceite:** paginação, filtros eficientes, isolamento financeiro e nenhuma credencial em respostas/logs.
- **Testes necessários:** CRUD, filtros, permissions, mascaramento, validação de CPF/CNPJ e acesso cruzado.
- **Riscos:** inferência de valores por endpoints sem proteção.
- **Arquivos prováveis:** serializers/views/permissions/urls/tests de `payments`.
- **Não alterar:** autenticação, audit sanitizer exceto inclusão pontual de chaves sensíveis.
- **Complexidade:** alta.

### DP-021 — Implementar registro e confirmação transacional de pagamento

- **Objetivo:** criar ações de agendar, confirmar e cancelar pagamento com histórico.
- **Motivo:** impedir dupla confirmação e manter rastreabilidade financeira.
- **Dependências:** DP-012, DP-015, DP-020.
- **Backend envolvido:** services transacionais, action serializers e viewset actions.
- **Frontend envolvido:** contratos na DP-022.
- **Banco envolvido:** lock da linha de pagamento; datas/ator e eventos atômicos.
- **Endpoints previstos:** `POST /api/payments/{id}/schedule/`, `/confirm/`, `/cancel/`.
- **Regras de negócio:** `select_for_update`; confirmação única; valor/data/forma obrigatórios; cancelamento com motivo; processo encerrado segue política explícita; evento/auditoria na mesma transação.
- **Permissões:** `schedule_payment`, `confirm_payment`, `cancel_payment` e acesso setorial/financeiro.
- **Critérios de aceite:** retries não duplicam confirmação; falha reverte tudo; retorno 409 em conflito.
- **Testes necessários:** transações, dupla confirmação, rollback, permissions, valores e eventos.
- **Riscos:** idempotência e regras de estorno fora do MVP.
- **Arquivos prováveis:** `payments/services.py`, serializers/views/tests, audit actions.
- **Não alterar:** status via PATCH genérico.
- **Complexidade:** alta.

### DP-022 — Criar telas de pagamentos e ações financeiras

- **Objetivo:** implementar lista, detalhe, cadastro/edição permitida, agendamento, confirmação e cancelamento.
- **Motivo:** entregar a operação financeira com filtros claros.
- **Dependências:** DP-018, DP-020, DP-021.
- **Backend envolvido:** nenhum salvo correções de contrato.
- **Frontend envolvido:** feature lazy `payments`, services/models, Reactive Forms e integração ao processo/menu.
- **Banco envolvido:** nenhum.
- **Endpoints previstos:** consumir DP-020/DP-021.
- **Regras de negócio:** moeda/data local sem perder precisão; mascarar dados; confirmação explícita; tratar 409; status vencido derivado.
- **Permissões:** menu/campos/ações por permissions financeiras.
- **Critérios de aceite:** filtros por status/vencimento/setor/fornecedor, fluxo acessível e valores exibidos corretamente.
- **Testes necessários:** services, forms, formatação decimal/data, permissions, loading/error/409.
- **Riscos:** arredondamento no JavaScript e exposição visual indevida.
- **Arquivos prováveis:** `frontend/src/app/features/payments/**`, rotas/sidebar/process detail.
- **Não alterar:** tema e autenticação.
- **Complexidade:** alta.

### DP-023 — Integrar comprovantes ao repositório de documentos

- **Objetivo:** anexar um ou mais comprovantes a pagamento confirmado usando a infraestrutura documental.
- **Motivo:** evitar mecanismo duplicado de upload e manter controle de acesso.
- **Dependências:** DP-017, DP-021.
- **Backend envolvido:** relação tipada pagamento-documento/anexo e service de upload/evento.
- **Frontend envolvido:** componente de comprovantes no detalhe/confirmar pagamento.
- **Banco envolvido:** FK ou tabela de papel de documento, conforme cardinalidade validada.
- **Endpoints previstos:** `GET/POST /api/payments/{id}/receipts/`, download via attachments.
- **Regras de negócio:** comprovante não substituído silenciosamente; remoção lógica; autorização financeira; confirmação pode exigir comprovante por política, não hard-code sem decisão.
- **Permissões:** `view_financial_data` e `manage_payment_receipt`.
- **Critérios de aceite:** upload/download seguro, evento “comprovante anexado” e histórico preservado.
- **Testes necessários:** arquivo, acesso, múltiplos comprovantes, remoção lógica e auditoria.
- **Riscos:** documentos financeiros acessíveis por endpoint documental genérico.
- **Arquivos prováveis:** apps `payments/documents`, frontend payments.
- **Não alterar:** MEDIA_ROOT/volumes ou excluir arquivo físico.
- **Complexidade:** alta.

### DP-024 — Criar consultas e alertas internos de vencimento

- **Objetivo:** identificar vencidos, vencendo hoje e próximos do vencimento, gerando notificações internas sem scheduler obrigatório.
- **Motivo:** dar visibilidade a obrigações financeiras no MVP.
- **Dependências:** DP-020, DP-021.
- **Backend envolvido:** queryset/service de deadlines e extensão de NotificationType/Service.
- **Frontend envolvido:** filtros/badges e links nas notificações.
- **Banco envolvido:** índice em vencimento/status; nenhuma duplicação de status vencido.
- **Endpoints previstos:** filtros `deadline=overdue|today|upcoming` em payments e resumo protegido.
- **Regras de negócio:** data local do sistema; janela próxima configurada em código/config pública apenas se necessário; geração idempotente; sem Celery nesta etapa.
- **Permissões:** destinatários com acesso financeiro ao setor.
- **Critérios de aceite:** classificação correta nas bordas de data e sem notificação duplicada.
- **Testes necessários:** datas/timezone, queryset, idempotência, destinatários e expiração.
- **Riscos:** sem scheduler os alertas dependem de gatilho por consulta/comando futuro.
- **Arquivos prováveis:** apps `payments/notifications`, frontend payments/notifications.
- **Não alterar:** Redis/Celery/Docker.
- **Complexidade:** média.

## Fase 5 — Dashboard, relatórios e busca

### DP-025 — Ampliar APIs e tela do dashboard por domínio

- **Objetivo:** mostrar processos em andamento/concluídos, pagamentos pendentes/vencidos e totais autorizados.
- **Motivo:** dar visão operacional sem substituir o dashboard atual.
- **Dependências:** DP-013, DP-020, DP-024.
- **Backend envolvido:** services/endpoints agregados de processos e finanças.
- **Frontend envolvido:** ampliar models/service/cards e manter cards existentes úteis.
- **Banco envolvido:** agregações e índices existentes; sem tabela de snapshot inicialmente.
- **Endpoints previstos:** `/api/dashboard/processes/`, `/api/dashboard/financial/`; manter `/api/dashboard/`.
- **Regras de negócio:** escopo setorial; totais financeiros só com permissão; “mês” e vencimento usam timezone configurado.
- **Permissões:** view process dashboard e `view_financial_data`.
- **Critérios de aceite:** cards corretos, consultas limitadas e ausência de dados não autorizados.
- **Testes necessários:** agregações, escopo, datas, permissions e componentes Angular.
- **Riscos:** endpoint monolítico lento e discrepância de moeda/período.
- **Arquivos prováveis:** `core/services/views`, apps de domínio, dashboard Angular.
- **Não alterar:** health/configurações e layout geral.
- **Complexidade:** alta.

### DP-026 — Criar APIs de relatórios de processos e pagamentos

- **Objetivo:** fornecer agregações filtráveis para os relatórios prioritários.
- **Motivo:** atender gestão inicial com Django ORM, sem BI separado.
- **Dependências:** DP-015, DP-020, DP-025.
- **Backend envolvido:** app/service de reports no domínio ou `core` apenas como orquestrador; serializers de filtros.
- **Frontend envolvido:** contratos na DP-027.
- **Banco envolvido:** `annotate`, `aggregate`, duração e índices; sem materialização prematura.
- **Endpoints previstos:** `GET /api/reports/processes/summary/`, `/time-by-sector/`, `GET /api/reports/payments/summary/`, `/by-sector/`, `/by-supplier/`.
- **Regras de negócio:** filtros por datas/setor/tipo/status/responsável/valor/finalidade; durações derivadas de movimentos; timezone e Decimal preservados.
- **Permissões:** `generate_reports`, escopo setorial e permissão financeira separada.
- **Critérios de aceite:** resultados reproduzíveis, paginação quando detalhado e queries documentadas.
- **Testes necessários:** agregações com fixtures de borda, filtros combinados, permissions e query count.
- **Riscos:** definição ambígua de tempo médio e gasto por período.
- **Arquivos prováveis:** services/views/urls/tests de reports/processes/payments.
- **Não alterar:** adicionar BI, Redis cache ou exportação assíncrona sem métricas.
- **Complexidade:** alta.

### DP-027 — Criar telas de relatórios e filtros

- **Objetivo:** apresentar tabelas/resumos de processos e pagamentos com filtros combináveis.
- **Motivo:** disponibilizar as APIs gerenciais sem nova biblioteca visual.
- **Dependências:** DP-026.
- **Backend envolvido:** nenhum salvo contrato.
- **Frontend envolvido:** feature lazy `reports`, Reactive Forms, tabelas e cards; gráficos somente com CSS/HTML se realmente úteis.
- **Banco envolvido:** nenhum.
- **Endpoints previstos:** consumir DP-026.
- **Regras de negócio:** manter filtros ao navegar, distinguir zero/sem dados, formatar moeda/duração e respeitar permission financeira.
- **Permissões:** rota/menu por `generate_reports`; seções financeiras separadas.
- **Critérios de aceite:** filtros solicitados, responsividade, acessibilidade e exportação fora do escopo.
- **Testes necessários:** service, filtros, renderização, permissions e estados vazios/erro.
- **Riscos:** expectativa de gráficos/exportação não incluídos.
- **Arquivos prováveis:** `frontend/src/app/features/reports/**`, rotas/sidebar.
- **Não alterar:** instalar biblioteca de chart/BI.
- **Complexidade:** média.

### DP-028 — Ampliar busca operacional com PostgreSQL

- **Objetivo:** buscar processos por número/texto, nota, fornecedor/CPF-CNPJ, setor, responsável e status.
- **Motivo:** localizar rapidamente o dossiê sem tecnologia adicional.
- **Dependências:** DP-009, DP-017, DP-020.
- **Backend envolvido:** filtros normalizados e, se medido necessário, busca PostgreSQL/trigram com extensão já suportada.
- **Frontend envolvido:** busca/filtros na lista de processos e navegação para resultados.
- **Banco envolvido:** índices B-tree e somente depois GIN/trigram justificado por plano de consulta.
- **Endpoints previstos:** ampliar `GET /api/processes/`; endpoint `/api/search/` apenas se uma consulta unificada provar valor.
- **Regras de negócio:** escopo aplicado antes da busca; CPF/CNPJ normalizado; limitar campos e tamanho da consulta.
- **Permissões:** resultados seguem policies do recurso e omitem financeiro sem permissão.
- **Critérios de aceite:** todos os campos prioritários pesquisáveis com resultados autorizados e desempenho aceitável.
- **Testes necessários:** busca, normalização, isolamento, caracteres especiais e query count/plano básico.
- **Riscos:** joins duplicarem resultados e buscas `%term%` degradarem.
- **Arquivos prováveis:** filters/querysets/tests de processes/payments, lista Angular.
- **Não alterar:** Elasticsearch, container ou dependência sem evidência.
- **Complexidade:** média.

## Fase 6 — Segurança, qualidade e otimização

### DP-029 — Endurecer segurança e ciclo de vida de arquivos

- **Objetivo:** revisar assinatura de arquivo, autorização de download, remoção lógica e retenção.
- **Motivo:** documentos e comprovantes elevam o impacto de uploads maliciosos e acesso indevido.
- **Dependências:** DP-017, DP-023.
- **Backend envolvido:** validators, download service/policy, auditoria e configuração documentada.
- **Frontend envolvido:** mensagens de rejeição e indicação de remoção.
- **Banco envolvido:** campos `removed_at/removed_by` se aprovados; sem apagar blob automaticamente.
- **Endpoints previstos:** manter downloads; ação explícita de inativação.
- **Regras de negócio:** deny by default, UUID, allowlist, tamanho, MIME/assinatura, headers seguros e auditoria sem conteúdo.
- **Permissões:** processo/setor + permissão documental/financeira.
- **Critérios de aceite:** cenários IDOR, spoofing, path traversal e arquivo removido cobertos.
- **Testes necessários:** security/API tests, headers, nomes, MIME, acesso cruzado e retenção lógica.
- **Riscos:** inspeção profunda exigir biblioteca/antivírus fora do escopo.
- **Arquivos prováveis:** `documents/validators/services/views/tests`, docs operacionais.
- **Não alterar:** volume/mídia física sem autorização.
- **Complexidade:** alta.

### DP-030 — Consolidar testes de concorrência e regras críticas

- **Objetivo:** criar suíte focada em locks, versões, tramitação e pagamentos simultâneos.
- **Motivo:** prevenir perda de atualização em operações administrativas irreversíveis.
- **Dependências:** DP-012, DP-021.
- **Backend envolvido:** `TransactionTestCase` e fixtures/services; sem ferramenta nova.
- **Frontend envolvido:** testes de tratamento de `409 Conflict`.
- **Banco envolvido:** PostgreSQL real no Compose para comportamento de lock.
- **Endpoints previstos:** actions existentes.
- **Regras de negócio:** um vencedor por versão; segunda confirmação/encaminhamento falha com estado atual; rollback íntegro.
- **Permissões:** cenários concorrentes também respeitam escopo.
- **Critérios de aceite:** testes reproduzíveis no container backend e frontend reage sem sobrescrever dados.
- **Testes necessários:** esta tarefa é a suíte; incluir threads/transações controladas e evitar sleeps frágeis.
- **Riscos:** testes concorrentes flakey e SQLite mascarar comportamento; usar PostgreSQL Compose.
- **Arquivos prováveis:** tests dos apps `processes/payments`, specs Angular.
- **Não alterar:** instalar pytest/E2E sem decisão.
- **Complexidade:** alta.

### DP-031 — Revisar integridade, retenção e privacidade da auditoria

- **Objetivo:** garantir cobertura de ações críticas e política explícita para dados financeiros/históricos.
- **Motivo:** rastreabilidade não pode virar fonte de vazamento ou crescimento ilimitado.
- **Dependências:** DP-015, DP-021, DP-029.
- **Backend envolvido:** audit actions, sanitizer, documentação e consultas; nenhuma exclusão automática inicialmente.
- **Frontend envolvido:** filtros adicionais da tela existente, se necessários.
- **Banco envolvido:** índices medidos; política de retenção documentada, não executada sem aprovação.
- **Endpoints previstos:** ampliar filtros de `/api/audit-logs/` sem permitir escrita.
- **Regras de negócio:** append-only; sem chaves/linhas bancárias completas, tokens ou conteúdo; acesso específico.
- **Permissões:** `audit.view_auditlog` e possível permissão financeira para detalhes sensíveis.
- **Critérios de aceite:** matriz evento→auditoria completa, sanitizer testado e política aprovada.
- **Testes necessários:** ações críticas, sanitização aninhada, read-only, filtros e permissions.
- **Riscos:** retenção legal depende de decisão organizacional externa.
- **Arquivos prováveis:** app `audit`, testes e documentação.
- **Não alterar:** apagar logs existentes automaticamente.
- **Complexidade:** média.

### DP-032 — Medir e otimizar consultas de hierarquia, timeline e relatórios

- **Objetivo:** eliminar N+1 e validar índices após dados representativos.
- **Motivo:** hierarquia, timeline e agregações podem degradar com volume.
- **Dependências:** DP-026, DP-028.
- **Backend envolvido:** querysets, `select_related/prefetch_related`, paginação e medição.
- **Frontend envolvido:** paginação/lazy loading de timeline e árvores grandes.
- **Banco envolvido:** índices adicionais somente apoiados por `EXPLAIN` e métricas.
- **Endpoints previstos:** mesmos contratos; nenhuma cache pública prematura.
- **Regras de negócio:** otimização não altera escopo nem consistência; limites máximos de página.
- **Permissões:** filtros aplicados antes de agregações/cache.
- **Critérios de aceite:** budgets de queries e tempos documentados em dataset de referência.
- **Testes necessários:** query count, paginação, carga básica e regressão funcional.
- **Riscos:** otimização prematura e cache com vazamento entre setores.
- **Arquivos prováveis:** querysets/services/tests e documentação de medição.
- **Não alterar:** Redis/containers ou adicionar serviços sem evidência.
- **Complexidade:** média.

### DP-033 — Atualizar documentação funcional e operacional do MVP

- **Objetivo:** consolidar regras, matriz de permissões, endpoints, fluxo e procedimentos seguros de migration/backup.
- **Motivo:** reduzir divergência entre implementação, operação e usuários.
- **Dependências:** DP-029, DP-030, DP-031, DP-032.
- **Backend envolvido:** nenhum funcional.
- **Frontend envolvido:** nenhum funcional.
- **Banco envolvido:** documentar migrations e rollback sem executar operações destrutivas.
- **Endpoints previstos:** catálogo final dos endpoints existentes.
- **Regras de negócio:** documentação reflete código validado; segredos nunca incluídos.
- **Permissões:** matriz Groups/Permissions/setores documentada.
- **Critérios de aceite:** README/docs atualizados, fluxos e riscos claros, comandos via Compose.
- **Testes necessários:** revisão de links/comandos e `docker compose config`; sem teste funcional novo.
- **Riscos:** documentação ficar desatualizada.
- **Arquivos prováveis:** `README.md`, `docs/*`, `.env.example` somente se variável aprovada.
- **Não alterar:** `.env` real, código funcional e infraestrutura.
- **Complexidade:** baixa.

## Mapa de dependências

```text
DP-002 Setores
├── DP-003 API setores ── DP-004 UI setores
├── DP-005 Usuário-setor ── DP-006 API/UI vínculos
└── DP-007 Política setorial
    └── DP-008 Modelo processo ── DP-009 API processo ── DP-010 UI processo
        └── DP-011 Movimento ── DP-012 Services transacionais ── DP-013 Actions/API ── DP-014 Timeline/UI
            └── DP-015 Eventos/auditoria
                ├── DP-016 Documento/anexo ── DP-017 API anexos ── DP-018 UI documentos
                │   └── DP-023 Comprovantes ── DP-029 Segurança de arquivos
                └── DP-019 Pagamento ── DP-020 API pagamentos ── DP-021 Confirmação
                    ├── DP-022 UI pagamentos
                    └── DP-024 Vencimentos

DP-013 + DP-020 + DP-024 ── DP-025 Dashboard
DP-015 + DP-020 + DP-025 ── DP-026 Relatórios ── DP-027 UI relatórios
DP-009 + DP-017 + DP-020 ── DP-028 Busca
DP-012 + DP-021 ── DP-030 Concorrência
DP-015 + DP-021 + DP-029 ── DP-031 Auditoria/privacidade
DP-026 + DP-028 ── DP-032 Performance
DP-029 + DP-030 + DP-031 + DP-032 ── DP-033 Documentação final
```

## Ordem recomendada

1. **Fundação:** DP-002 a DP-007. Aprovar conceitos de setor, vínculo e matriz de acesso antes de qualquer processo.
2. **Núcleo de processo:** DP-008 a DP-015. Validar estados e ações com usuários reais antes de documentos financeiros.
3. **Dossiê documental:** DP-016 a DP-018. Tratar a migration do documento legado como mudança de alto risco e executar em etapas.
4. **Financeiro:** DP-019 a DP-024. Separar cadastro, autorização, confirmação, comprovante e alertas.
5. **Leitura gerencial:** DP-025 a DP-028. Criar dashboard/relatórios/busca sobre modelos estabilizados.
6. **Hardening:** DP-029 a DP-033. Consolidar segurança, concorrência, auditoria, desempenho e documentação.

## Decisões pendentes antes da implementação

- Formato e regra de geração do número de processo (sequencial global, anual e/ou por organização).
- Abrangência de visualização: somente setor atual, setores de origem/destino, ancestrais/descendentes ou participantes históricos.
- Se recebimento explícito é obrigatório após todo encaminhamento.
- Pré-condições para conclusão quando há pagamento pendente.
- Cardinalidade e obrigatoriedade de comprovantes.
- Campos bancários realmente necessários e respectiva política de retenção/mascaramento.
- Prazo que define “próximo do vencimento”.
- Definição gerencial de tempo por setor e período financeiro dos relatórios.

Essas decisões devem ser registradas nas issues correspondentes antes de migrations ou regras irreversíveis.
