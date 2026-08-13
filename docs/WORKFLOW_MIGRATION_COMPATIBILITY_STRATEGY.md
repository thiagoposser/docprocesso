# Estratégia de migração e compatibilidade do workflow

Este documento define o plano seguro de ativação da hierarquia e do workflow do DocProcesso. Ele não autoriza executar migrations, backfill, rebuild, restauração ou alteração em produção. Cada execução exige janela aprovada, backup restaurável e revisão dos resultados do ambiente alvo.

## Estado observado

O inventário abaixo foi obtido em 13/08/2026 no ambiente Docker Compose de desenvolvimento, por comandos somente de leitura. Ele não substitui um inventário do ambiente que será migrado.

| Item | Estado observado |
|---|---:|
| Unidades organizacionais | 0 |
| Setores | 6 |
| Funções organizacionais | 0 |
| Vínculos usuário-setor | 0 |
| Processos | 0 |
| Movimentações | 0 |
| Documentos | 1 |
| Anexos | 1 |
| Pagamentos | 0 |
| Comprovantes | 0 |

O schema implantado está atrás do código:

- `processes.0001` a `processes.0004` estão aplicadas;
- `processes.0005` a `processes.0014` estão pendentes;
- `documents.0001` a `documents.0003` estão aplicadas e `documents.0004` está pendente;
- `payments.0001` a `payments.0003` estão aplicadas e `payments.0004` está pendente;
- `sectors.0001` a `sectors.0006` estão aplicadas.

Isso explica por que o modelo Django atual referencia colunas ainda inexistentes no banco em execução. Até a aplicação coordenada das migrations pendentes, endpoints que consultem esses campos podem falhar. Não se deve resolver essa divergência com `--fake`, edição de migration histórica ou recriação do banco.

## Princípios obrigatórios

1. Preservar linhas, arquivos físicos, histórico e auditoria.
2. Introduzir primeiro tabelas e campos opcionais; preencher dados depois; tornar obrigatório somente em uma fase futura e aprovada.
3. Fazer backfill idempotente, em lotes limitados e com checkpoint observável.
4. Não usar defaults organizacionais que concedam permission ou ampliem escopo.
5. Manter leitura de registros legados enquanto houver campos nulos.
6. Separar rollback de aplicação, rollback de dados e desativação funcional.
7. Nunca editar migrations aplicadas, remover volumes ou apagar arquivos para corrigir inconsistências.
8. Tratar o PostgreSQL do ambiente alvo como fonte de verdade; contagens locais são apenas referência.

## Inventário obrigatório por ambiente

Antes de qualquer aplicação, registrar em artefato operacional protegido:

- versão do commit e imagem implantada;
- resultado de `showmigrations --plan`;
- contagem por tabela e tamanho aproximado;
- quantidade de processos por estado, com/sem setor atual e por tipo;
- documentos independentes e vinculados, origem de arquivo/URL e anexos ativos/inativos;
- pagamentos por estado e comprovantes associados;
- unidades, setores sem unidade, funções e vínculos ativos, expirados ou sem função;
- referências protegidas e registros órfãos detectados por consultas explícitas;
- volume e caminho lógico de `MEDIA_ROOT`, sem listar conteúdo sensível;
- permissões e grupos existentes, sem exportar segredos.

O inventário deve ser repetido imediatamente antes e depois de cada fase. Diferenças não previstas interrompem o rollout.

## Mapa de entidades e tratamento legado

| Entidade | Campo/contexto novo | Compatibilidade temporária | Regra de backfill |
|---|---|---|---|
| `Sector` | unidade e hierarquia | unidade/pai podem permanecer nulos | associação aprovada por código estável; nunca inferir unidade por nome ambíguo |
| `UserSectorMembership` | função, vigência, principal/gerência | usuário legado pode não ter vínculo | importar somente vínculos homologados; não criar vínculo amplo por conveniência |
| `AdministrativeWorkflow` e versões | grafo versionado | tipos sem workflow continuam legados | criar/publicar fluxo por configuração aprovada e código estável |
| `ProcessType` | workflow associado | tipo ativo pode ficar sem workflow | associar somente quando todos os processos futuros daquele tipo puderem usar a versão publicada |
| `AdministrativeProcess` | versão, etapa e responsabilidade | campos permanecem nulos para legado | classificar caso a caso por tipo/estado; ambiguidades vão para fila manual |
| `ProcessMovement` | versão, transição, etapas e snapshot | histórico antigo continua válido sem novo contexto | nunca reescrever fatos; enriquecer somente quando a origem for determinística e auditável |
| `Document` | processo e papel documental | documento independente e campos legados continuam válidos | vínculo apenas por relação comprovada; arquivo/URL e caminho físico são preservados |
| `Attachment` | etapa, setor, função e snapshot | anexos antigos podem manter contexto nulo | capturar contexto apenas quando processo/etapa histórica forem demonstráveis |
| `Payment` | versão e etapa | pagamento legado permanece operável pelos endpoints compatíveis | vincular ao contexto financeiro somente com evidência do processo na data do registro |
| `PaymentReceipt` | anexo protegido | comprovantes existentes continuam no endpoint financeiro | não mover nem duplicar arquivo; preservar relação e remoção lógica |
| Auditoria/eventos | novos eventos e snapshots | logs existentes são imutáveis | registrar o backfill como operação própria; nunca alterar logs anteriores |

## Plano de rollout

### Fase 0 — decisão e preparação

- homologar mapa Unidade → Setor → Função e responsáveis;
- homologar quais tipos recebem cada workflow;
- definir proprietário das exceções e prazo de compatibilidade;
- obter backup e provar restauração em ambiente isolado;
- medir duração das migrations em cópia representativa;
- definir janela, responsáveis, canal de incidentes e critérios de abortar.

Saída: inventário assinado, backup restaurável e decisão explícita de prosseguir.

### Fase 1 — expandir schema

Aplicar somente migrations aditivas já revisadas, na ordem do grafo do Django. No estado atual, a cadeia de `processes.0005–0014` também precede os campos contextuais de documentos e pagamentos.

Critérios:

- `migrate --plan` corresponde à revisão;
- nenhuma operação remove/renomeia coluna com dados;
- locks e duração ficam dentro da janela;
- `showmigrations`, `check` e smoke tests passam;
- contagens de registros e arquivos não mudam.

Se falhar, interromper tráfego de escrita conforme o runbook e decidir entre reversão comprovadamente não destrutiva ou restauração do backup. Não usar `--fake` para mascarar falha.

### Fase 2 — compatibilidade de aplicação

Implantar código capaz de:

- ler campos novos nulos;
- manter processos sem workflow como legados;
- aceitar contratos antigos ainda publicados, sem permitir forjar origem/responsabilidade;
- usar endpoints de transição para processos com workflow;
- manter endpoints financeiros compatíveis e exigir etapa somente quando houver contexto de workflow;
- preservar documento independente, arquivo/URL legado e comprovantes no endpoint financeiro.

Durante esta fase, escrita nova deve preencher contexto quando determinístico, mas não deve tornar campos obrigatórios no banco.

### Fase 3 — backfill idempotente

O backfill futuro deve ser um comando versionado, separado da migration de schema, com:

- `--dry-run`, tamanho de lote e limite opcional;
- seleção por chave primária estável;
- transação por lote, não uma transação global longa;
- bloqueio/controle para evitar duas execuções concorrentes;
- checkpoint e totais `eligible`, `updated`, `unchanged`, `ambiguous`, `failed`;
- nova execução sem duplicar versões, movimentos, eventos, documentos ou permissões;
- log sem tokens, arquivos, dados bancários ou conteúdo documental.

Ordem de dados:

1. unidades e associação segura de setores;
2. funções e vínculos homologados;
3. workflows/versionamentos/etapas/transições;
4. associação de tipos de processo;
5. processos não ambíguos;
6. contexto opcional de anexos e pagamentos;
7. relatório de legados/ambiguidades para tratamento manual.

Movimentações e auditoria não devem ser sintetizadas como se tivessem ocorrido no passado. Quando necessário, criar um evento explícito de migração, separado do histórico original.

### Fase 4 — ativação controlada

Ativar por tipo de processo ou unidade, nunca globalmente sem piloto:

1. equipe interna e poucos tipos sem dados ambíguos;
2. monitorar erros HTTP, conflitos, duração de consultas e divergência dashboard/workbox;
3. ampliar gradualmente após período definido;
4. manter chave de desativação funcional ou capacidade de desassociar somente novas criações, sem apagar contexto já gravado.

Nenhum toggle pode ignorar permission, vínculo ou etapa no backend.

### Fase 5 — contrair somente após aceite separado

Campos opcionais só podem virar obrigatórios quando:

- não houver nulos elegíveis;
- exceções legadas estiverem formalmente classificadas;
- contratos antigos não tiverem consumidores ativos;
- rollback e duração da constraint tiverem sido testados em cópia;
- houver nova Issue e autorização explícita.

Remover campos/endpoints legados não faz parte da DP-063.

## Compatibilidade de contratos

| Contrato | Durante transição | Destino |
|---|---|---|
| `POST /api/processes/` | origem vem de vínculo autorizado; tipo sem workflow ainda cria legado | tipos ativados resolvem versão/etapa no backend |
| ações legadas `open/forward/...` | permanecem para processo legado | processos com workflow usam `available-actions` e `transitions` |
| `GET /api/processes/` e workbox | campos novos podem ser nulos | clientes devem tratar `workflow_version/current_stage/responsibility` nulos |
| documentos globais | documentos independentes e arquivo/URL legado continuam válidos | novos anexos de processo recebem snapshot contextual |
| `POST /api/payments/` e actions | processo legado mantém comportamento compatível | processo com workflow exige ação financeira disponível na etapa |
| comprovantes | acesso pelo módulo financeiro, arquivo preservado | snapshot contextual quando disponível |

Depreciação exige telemetria de uso, comunicação, data e Issue própria. Resposta silenciosamente incompatível não é permitida.

## Validação em cópia isolada

Não usar o banco persistente de desenvolvimento ou produção como laboratório. Em ambiente isolado autorizado:

1. restaurar uma cópia sanitizada do backup;
2. registrar contagens e checksums/agrupamentos não sensíveis;
3. aplicar migrations na ordem planejada;
4. executar o backfill primeiro em `--dry-run`, depois de fato;
5. repetir contagens, integridade referencial e relatório de ambiguidades;
6. executar testes de contratos legados e novos;
7. validar arquivos por existência/tamanho sem expor conteúdo;
8. medir duração, locks e planos das consultas críticas;
9. exercitar desativação funcional e restauração completa.

Gates mínimos:

- zero linha ou arquivo perdido;
- zero elevação de acesso por vínculo/default;
- contagens antes/depois explicadas;
- backfill repetido produz `updated=0`;
- processos legados continuam legíveis;
- processos ativados respeitam etapa, setor, função e versionamento;
- dashboard e workbox retornam contagens equivalentes;
- pagamentos e comprovantes não vazam para usuário sem permissions financeiras.

## Rollback e resposta a incidente

Há três respostas diferentes:

1. **Desativação funcional:** interromper novas ativações e manter leitura dos dados já escritos. É a primeira opção quando o schema está íntegro.
2. **Reversão de release:** voltar a aplicação somente se a versão anterior tolerar o schema expandido e os campos nulos/preenchidos.
3. **Restauração:** usar backup validado quando houve corrupção/perda ou a reversão de migration não é segura. Exige coordenação e janela própria.

Migration reversa só pode ser usada após leitura da operação `reverse` e prova de que ela não removerá dados. Campos com backfill nunca devem ser descartados como rollback automático.

Critérios de abortar imediatamente:

- erro de integridade ou contagem inesperada;
- lock acima do limite aprovado;
- aumento de 403/404/409/500 fora da linha de base;
- usuário ganhando acesso a outro setor;
- arquivo ou comprovante inacessível;
- backfill não idempotente;
- divergência persistente entre workbox, dashboard e estado do processo.

## Comandos permitidos para preparação

Somente leitura/validação, ajustados aos nomes reais do Compose:

```bash
docker compose ps
docker compose config
docker compose exec -T backend python manage.py showmigrations --plan
docker compose exec -T backend python manage.py migrate --plan
docker compose exec -T backend python manage.py makemigrations --check --dry-run
docker compose exec -T backend python manage.py check
```

`migrate`, comandos de backfill, restore e rebuild não devem ser executados sem autorização explícita. Backups não devem ser versionados no repositório.

## Checklist de aprovação

- [ ] inventário do ambiente alvo anexado e revisado;
- [ ] divergência schema/código eliminada primeiro em cópia isolada;
- [ ] backup restaurado com sucesso em ambiente isolado;
- [ ] migrations e locks medidos com volume representativo;
- [ ] mapa organizacional e workflows homologados;
- [ ] backfill idempotente implementado em Issue separada e aprovado;
- [ ] matriz de permissions comparada antes/depois;
- [ ] contratos antigos e novos validados;
- [ ] smoke tests de frontend/backend e arquivos aprovados;
- [ ] observabilidade, responsáveis e critérios de abortar definidos;
- [ ] piloto aprovado antes da expansão;
- [ ] constraints obrigatórias/depreciação tratadas em Issue separada.

## Decisões ainda necessárias

- quais tipos e unidades entram no piloto;
- fonte oficial para mapear setores às unidades e usuários às funções;
- política para processos legados ambíguos;
- duração do período de compatibilidade;
- limites aceitáveis de lock, indisponibilidade e taxa de erro;
- retenção e localização protegida dos backups;
- responsável por aprovar exceções e reconciliação pós-rollout.

Até essas decisões serem registradas, o schema pode ser expandido somente em cópia isolada; backfill e ativação geral permanecem bloqueados.
