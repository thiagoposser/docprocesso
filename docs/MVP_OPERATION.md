# Guia funcional e operacional do MVP do DocProcesso

Este documento descreve o estado implementado até a DP-033. O ambiente Docker Compose é a referência; não execute comandos do projeto diretamente no host.

## Fluxo funcional

1. Um administrador configura setores, usuários, vínculos e permissões.
2. Um usuário autorizado cria um processo em seu setor de origem.
3. O processo é aberto, encaminhado, recebido, devolvido, concluído, reaberto, cancelado ou arquivado conforme estado, versão e permissão.
4. Documentos e anexos formam o dossiê. Arquivos usam caminhos UUID, allowlist, limite, validação de MIME/assinatura e remoção lógica.
5. Pagamentos vinculam processo, setor e fornecedor. Agendamento, confirmação e cancelamento usam transação e lock; comprovantes só entram em pagamentos confirmados.
6. Dashboard, relatórios e busca respeitam o escopo setorial. Dados financeiros exigem permissão separada.
7. Ações críticas geram histórico funcional e auditoria append-only sanitizada.

## Matriz de acesso

Permissões Django e vínculo setorial ativo são cumulativos; o backend é sempre a autoridade.

| Área | Permissões principais | Regra setorial/estado |
|---|---|---|
| Setores | `view/add/change_sector`, `manage_sector` | escrita administrativa; ciclos são rejeitados |
| Vínculos | `manage_user_sector_membership` | usuário e setor precisam estar ativos |
| Processos | `view/add/change_administrativeprocess` | setor atual, ou origem enquanto não há setor atual |
| Tramitação | `open/forward/receive/return/complete/reopen/cancel/archive_administrativeprocess` | ação, estado, versão e setor; reabertura exige responsável |
| Documentos | `view/change_document`, `add/view/change_attachment`, `manage_document`, `manage_attachment` | processo e setor; encerramento restringe novos anexos |
| Pagamentos | `view_payment`, `view_financial_data`, `add/change_payment` | membership no setor financeiro e acesso ao processo |
| Ações financeiras | `schedule_payment`, `confirm_payment`, `cancel_payment` | lock de linha e estados permitidos |
| Comprovantes | `view_paymentreceipt`, `manage_payment_receipt` | pagamento confirmado, processo/setor e permissão financeira |
| Relatórios | `core.generate_reports` | processos escopados; finanças exigem também permissões financeiras |
| Auditoria | `audit.view_auditlog` | consulta read-only; registros imutáveis |

Superusuário ignora o recorte de membership onde explicitamente previsto. Grupos são coleções de permissões; pertencer a um grupo não substitui as policies setoriais.

## Catálogo de endpoints

Todos usam prefixo `/api/`. Coleções são paginadas quando aplicável.

| Domínio | Endpoints |
|---|---|
| Autenticação | `POST auth/login/`, `POST auth/refresh/`, `POST auth/logout/`, `GET auth/me/` |
| Setores | `GET/POST sectors/`, `GET/PATCH sectors/{id}/`, `GET sectors/tree/`, `GET/POST user-sector-memberships/`, `GET/PATCH user-sector-memberships/{id}/` |
| Processos | `GET/POST processes/`, `GET/PATCH processes/{id}/`, `GET process-types/` |
| Tramitação | `POST processes/{id}/open|forward|receive|return|complete|reopen|cancel|archive/` |
| Dossiê | `GET processes/{id}/timeline/`, `GET/POST processes/{id}/documents/` |
| Documentos | `GET/POST documents/`, `GET/PATCH documents/{id}/`, `GET documents/{id}/download/`, `GET/POST documents/{id}/attachments/` |
| Anexos | `GET attachments/{id}/`, `GET attachments/{id}/download/`, `PATCH attachments/{id}/deactivate/` |
| Categorias | `GET/POST document-categories/`, `GET/PATCH document-categories/{id}/` |
| Fornecedores | `GET/POST suppliers/`, `GET/PATCH suppliers/{id}/` |
| Pagamentos | `GET/POST payments/`, `GET/PATCH payments/{id}/`, `POST payments/{id}/schedule|confirm|cancel/` |
| Comprovantes | `GET/POST payments/{id}/receipts/` e endpoints protegidos do anexo |
| Vencimentos | `GET payments/?deadline=overdue|today|upcoming`, `GET payments/deadline-summary/` |
| Dashboard | `GET dashboard/`, `GET dashboard/processes/`, `GET dashboard/financial/` |
| Relatórios | `GET reports/processes/summary/`, `GET reports/processes/time-by-sector/`, `GET reports/payments/summary/`, `GET reports/payments/by-sector/`, `GET reports/payments/by-supplier/` |
| Auditoria | `GET audit-logs/`, `GET audit-logs/{id}/` |
| Notificações | `GET notifications/`, `GET notifications/{id}/`, `PATCH notifications/{id}/read/`, `POST notifications/read-all/`, `GET notifications/unread-count/` |
| Sistema | `GET health/`, `GET settings/public/`, `GET/PATCH settings/` |

## Operação segura com Compose

```bash
docker compose ps
docker compose config
docker compose exec backend python manage.py check
docker compose exec backend python manage.py showmigrations
docker compose exec frontend npm run build
```

Não execute `npm install`, `pip install`, rebuild ou migrations por rotina sem revisar a mudança. PostgreSQL e Redis dos containers são as fontes de dados.

### Backup antes de migrations

Crie um arquivo fora do repositório e proteja seu acesso:

```bash
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > docprocesso-AAAA-MM-DD.dump
```

Valide que o comando terminou com código zero e que o arquivo não está vazio. Um backup só é confiável após teste de restauração em ambiente isolado autorizado. Nunca versione dumps ou segredos.

### Aplicação e rollback de migration

1. Leia a migration e classifique impacto, lock e reversibilidade.
2. Execute `docker compose exec backend python manage.py makemigrations --check --dry-run`.
3. Faça e valide o backup.
4. Aplique com `docker compose exec backend python manage.py migrate` em janela aprovada.
5. Execute `check`, testes proporcionais e smoke tests.

Rollback não é automático. Só use `python manage.py migrate <app> <migration_anterior>` depois de confirmar que a operação reversa não perde dados e receber autorização. Se houver perda potencial, restaure um backup validado em procedimento coordenado. Não edite migrations já aplicadas e não remova volumes.

## Validação e diagnóstico

```bash
docker compose exec backend python manage.py test --keepdb
docker compose logs backend frontend nginx
```

O banco `test_app_db` é descartável, mas sua exclusão ainda exige autorização. Falha de ferramenta no host não representa falha do projeto quando a validação equivalente passa no container.

## Riscos e decisões pendentes

- Antivírus, armazenamento de objetos e URLs temporárias dependem do risco/ambiente de produção.
- Prazo legal de retenção de auditoria precisa de aprovação organizacional; hoje não há expurgo.
- Backups, restauração, TLS, observabilidade e secrets externos precisam ser operados pela plataforma de produção.
- O formato opaco do número do processo deve ser revisto apenas se houver exigência normativa de sequência.
- Testes Angular automatizados dependem da correção da infraestrutura registrada na Issue #46; o build no container é o gate atual.

Consulte também [política de acesso setorial](SECTOR_ACCESS_POLICY.md), [auditoria](AUDIT_POLICY.md), [desempenho](QUERY_PERFORMANCE.md) e [arquitetura](ARCHITECTURE.md).
