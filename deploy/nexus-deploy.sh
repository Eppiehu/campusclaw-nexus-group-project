#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
test -s .env.nexus.local || { echo 'Create .env.nexus.local from .env.nexus.example first' >&2; exit 1; }
docker compose --env-file .env.nexus.local -f docker-compose.nexus.yml config --quiet
docker compose --env-file .env.nexus.local -f docker-compose.nexus.yml build api
docker compose --env-file .env.nexus.local -f docker-compose.nexus.yml up -d db redis
docker compose --env-file .env.nexus.local -f docker-compose.nexus.yml run --rm --no-deps api python scripts/nexus_init.py
docker compose --env-file .env.nexus.local -f docker-compose.nexus.yml up -d api worker scheduler
docker compose --env-file .env.nexus.local -f docker-compose.nexus.yml ps
