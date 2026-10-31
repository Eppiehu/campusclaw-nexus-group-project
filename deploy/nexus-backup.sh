#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
test -s .env.nexus.local || { echo 'Missing .env.nexus.local' >&2; exit 1; }
umask 077
backup_dir=${NEXUS_BACKUP_DIR:-"$root/backups"}
mkdir -p "$backup_dir"
target="$backup_dir/nexus-$(date -u +%Y%m%dT%H%M%SZ).sql"
docker compose --env-file .env.nexus.local -f docker-compose.nexus.yml exec -T db pg_dump -U nexus nexus > "$target"
test -s "$target"
echo 'Nexus database backup completed'
