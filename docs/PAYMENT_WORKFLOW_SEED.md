# Fluxo inicial de Pagamento Administrativo

O comando abaixo configura o fluxo usando códigos de setores existentes, sem IDs fixos e sem sobrescrever configurações incompatíveis:

```bash
docker compose exec backend python manage.py seed_payment_workflow \
  --requester-sector-code PROTOCOLO \
  --management-sector-code GERENCIA \
  --finance-sector-code FINANCEIRO
```

O comando é idempotente: execuções repetidas validam o mesmo grafo sem duplicar fluxo, versão, etapas, transições, funções ou tipo de processo. Os três setores devem existir e estar ativos. Nenhuma permission é concedida e nenhum usuário ou superusuário é criado.
