# Arquitetura

O navegador acessa o Nginx, que encaminha `/api` e `/admin` ao Django e as demais rotas ao Angular. Django usa PostgreSQL para persistência e Redis como base para cache, filas ou sessões futuras. PgAdmin é uma ferramenta operacional, não uma dependência da aplicação.

Novos domínios de backend devem ser apps em `backend/apps/`. No frontend, funcionalidades crescem como áreas lazy-loaded em `src/app`, enquanto integrações globais permanecem em `core` e componentes reutilizáveis em `shared`.
