#!/usr/bin/env sh
set -eu

# Rebuild images and recreate services after dependency or infrastructure updates.
docker compose pull
docker compose build --pull
docker compose up -d --remove-orphans
docker compose ps
