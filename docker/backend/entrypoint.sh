#!/bin/sh
set -eu

# Migrations are idempotent and keep fresh environments ready to use.
python manage.py migrate --noinput
exec "$@"
