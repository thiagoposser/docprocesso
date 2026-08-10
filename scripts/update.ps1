$ErrorActionPreference = 'Stop'

# Equivalent cross-platform maintenance workflow for PowerShell users.
docker compose pull
docker compose build --pull
docker compose up -d --remove-orphans
docker compose ps
