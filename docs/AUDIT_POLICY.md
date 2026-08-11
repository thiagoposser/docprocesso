# Política de auditoria do DocProcesso

## Integridade e acesso

Os registros são append-only: a aplicação permite criação e consulta, mas bloqueia atualização e exclusão tanto na API quanto no ORM. A consulta exige `audit.view_auditlog`. Logs não armazenam senhas, tokens, cookies, credenciais, dados bancários completos, chaves Pix ou conteúdo/binário de arquivos.

## Matriz de eventos

| Evento | Ação de auditoria | Conteúdo permitido |
|---|---|---|
| Login, logout e falha | `LOGIN`, `LOGOUT`, `LOGIN_FAILED` | usuário/identificador, sem senha ou token |
| Usuários e cadastros | `CREATE`, `UPDATE`, `ACTIVATE`, `DEACTIVATE` | campos allowlisted e diferenças sanitizadas |
| Tramitação de processo | `PROCESS_WORKFLOW` | estado, setor, versão e ação |
| Evento histórico | `PROCESS_EVENT` | identificadores e payload sanitizado |
| Agendar, confirmar ou cancelar pagamento | `PAYMENT_WORKFLOW` | estado anterior/novo; sem conta, chave ou comprovante |
| Upload/inativação de anexo ou comprovante | `FILE_LIFECYCLE` | identificadores e tipo de origem; nunca conteúdo |
| Visualização/download | `DOCUMENT_VIEW`, `DOCUMENT_DOWNLOAD` | identificador e nome sanitizado |
| Configuração pública | `SETTINGS_CHANGED` | campos não secretos allowlisted |

## Retenção

Não há exclusão automática. Os logs permanecem retidos por prazo indeterminado até que a organização aprove formalmente prazo legal, responsáveis, procedimento de autorização e evidência de descarte. Qualquer rotina futura de expurgo deve ser uma tarefa separada, auditada e precedida de backup e aprovação explícita; esta política não autoriza apagar registros existentes.
