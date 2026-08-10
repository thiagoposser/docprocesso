#!/bin/sh
set -eu

# Renderiza o cadastro do servidor sem gravar credenciais no repositório.
sed \
  -e "s/\${POSTGRES_HOST}/$POSTGRES_HOST/g" \
  -e "s/\${POSTGRES_PORT}/$POSTGRES_PORT/g" \
  -e "s/\${POSTGRES_DB}/$POSTGRES_DB/g" \
  -e "s/\${POSTGRES_USER}/$POSTGRES_USER/g" \
  /pgadmin4/servers.template.json > /tmp/servers.json

export PGADMIN_SERVER_JSON_FILE=/tmp/servers.json
exec /entrypoint.sh
