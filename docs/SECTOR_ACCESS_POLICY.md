# Matriz de acesso setorial

O backend decide acesso combinando autenticação, Permission Django, vínculo ativo, setor ativo e estado permitido do recurso. Groups concedem capacidades por meio de Permissions; `UserSectorMembership` limita onde elas podem ser exercidas. Somente superusuário possui bypass. Guards e helpers Angular existem apenas para experiência do usuário.

| Capacidade futura | Permission prevista | Escopo adicional |
|---|---|---|
| Visualizar processo | `processes.view_administrativeprocess` | vínculo ativo no setor permitido |
| Criar processo | `processes.add_administrativeprocess` | vínculo ativo no setor de origem |
| Editar processo | `processes.change_administrativeprocess` | vínculo e estado editável |
| Encaminhar | `processes.forward_administrativeprocess` | vínculo no setor atual e estado permitido |
| Receber | `processes.receive_administrativeprocess` | vínculo no destino |
| Devolver | `processes.return_administrativeprocess` | vínculo no setor atual e estado permitido |
| Finalizar | `processes.complete_administrativeprocess` | vínculo; gestor quando a regra exigir |
| Reabrir | `processes.reopen_administrativeprocess` | vínculo de gestor e estado concluído |
| Dados financeiros | `payments.view_financial_data` | vínculo no setor da despesa |
| Confirmar pagamento | `payments.confirm_payment` | vínculo e estado financeiro permitido |
| Relatórios | `reports.generate_reports` | resultados filtrados aos setores acessíveis |
| Administrar setores | `sectors.manage_sector` | regra administrativa existente |
| Administrar vínculos | `sectors.manage_user_sector_membership` | regra administrativa existente |

Recursos futuros devem chamar `evaluate_sector_access` a partir de services/permissions e testar todas as negativas. Estar autenticado, pertencer a Group ou possuir vínculo isoladamente nunca é suficiente.
