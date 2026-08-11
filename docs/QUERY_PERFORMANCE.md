# Medição de consultas do DocProcesso

## Dataset de referência

Os budgets automatizados usam árvore setorial com múltiplos níveis, timeline com 75 eventos e relatórios com processos e pagamentos em setores autorizados e não autorizados. A suíte roda contra PostgreSQL no Docker Compose.

## Budgets

| Fluxo | Limite automatizado | Estratégia |
|---|---:|---|
| Árvore de setores | 4 queries após caches normais | uma consulta com `select_related`, montagem em memória |
| Timeline paginada | 8 queries por requisição autenticada | contagens e duas consultas limitadas ao horizonte da página |
| Resumo de processos | 6 queries | agregações ORM sobre queryset já escopado |
| Pagamentos por fornecedor | 4 queries | uma agregação agrupada sobre queryset escopado |

A timeline retorna no máximo 20 itens por página. As consultas de movimentos e eventos carregam no máximo `página × 20` registros de cada fonte, evitando carregar o histórico completo na primeira página.

## Índices e cache

Os índices atuais cobrem chaves estrangeiras, estados e datas usadas nos filtros prioritários. Não foi adicionado índice nesta tarefa porque os budgets foram atendidos e não houve plano `EXPLAIN` demonstrando ganho líquido. Redis, cache compartilhado e novos containers permanecem fora do fluxo para impedir mistura de escopos setoriais.
