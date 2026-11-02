#!/bin/sh
# Run from anywhere: sh deploy/nexus-deploy.sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"

if [ "${1:-}" = "--help" ]; then
  echo 'Usage: sh deploy/nexus-deploy.sh [--check]'
  echo 'First run creates a private .env.nexus.local with random demo credentials.'
  echo 'Set NEXUS_PORT in that file when the default port 8080 is occupied.'
  exit 0
fi
if [ "${1:-}" != "" ] && [ "${1:-}" != "--check" ]; then
  echo 'Unknown option; use --help' >&2
  exit 2
fi

command -v docker >/dev/null 2>&1 || { echo 'Docker is required' >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo 'Docker Compose plugin is required' >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo 'Docker daemon is unavailable' >&2; exit 1; }

env_file=.env.nexus.local
if [ ! -e "$env_file" ]; then
  command -v openssl >/dev/null 2>&1 || { echo 'OpenSSL is required to create demo credentials' >&2; exit 1; }
  umask 077
  signing_key=$(openssl rand -hex 32)
  db_password=$(openssl rand -hex 24)
  teacher_password=$(openssl rand -hex 16)
  student_password=$(openssl rand -hex 16)
  cat > "$env_file" <<EOF
CAMPUSCLAW_EDITION=nexus
NEXUS_SIGNING_KEY=$signing_key
NEXUS_DB_PASSWORD=$db_password
NEXUS_TEACHER_PASSWORD=$teacher_password
NEXUS_STUDENT_PASSWORD=$student_password
NEXUS_PORT=8080
NEXUS_BIND_ADDRESS=0.0.0.0
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.deepseek.com
NEXUS_MODEL=deepseek-chat
NEXUS_SECURE_COOKIE=0
HF_HUB_OFFLINE=1
EOF
  unset signing_key db_password teacher_password student_password
  echo "Created private $env_file. Edit NEXUS_PORT or OPENAI_API_KEY there if needed."
fi

if [ ! -f "$env_file" ] || [ ! -s "$env_file" ]; then
  echo "$env_file must be a nonempty regular file" >&2
  exit 1
fi

dc() { docker compose --env-file "$env_file" -f docker-compose.nexus.yml "$@"; }
dc config --quiet
port=$(sed -n 's/^NEXUS_PORT=//p' "$env_file" | tail -n 1)
port=${port:-8080}
case "$port" in
  ''|*[!0-9]*) echo 'NEXUS_PORT must be numeric' >&2; exit 1 ;;
esac
if [ -z "$(dc ps -q api)" ] && command -v ss >/dev/null 2>&1 && ss -lnt "( sport = :$port )" | grep -q LISTEN; then
  echo "Port $port is already in use. Set another NEXUS_PORT in $env_file; no service was changed." >&2
  exit 1
fi
if [ "${1:-}" = "--check" ]; then
  echo 'PASS: Docker, Compose and configuration preflight'
  exit 0
fi

echo 'Building Nexus image (first build downloads public dependencies and embedding model)...'
dc build api
echo 'Starting database and Redis...'
dc up -d db redis

wait_healthy() {
  service=$1
  attempts=$2
  while [ "$attempts" -gt 0 ]; do
    cid=$(dc ps -q "$service")
    if [ -n "$cid" ]; then
      status=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid")
      if [ "$status" = healthy ]; then return 0; fi
      if [ "$status" = unhealthy ] || [ "$status" = exited ]; then
        echo "$service is $status; inspect with: docker compose --env-file $env_file -f docker-compose.nexus.yml logs $service" >&2
        return 1
      fi
    fi
    attempts=$((attempts - 1))
    sleep 2
  done
  echo "$service did not become healthy in time" >&2
  return 1
}

wait_healthy db 60
wait_healthy redis 30
echo 'Running database migrations and idempotent demo seed...'
dc run --rm --no-deps api python scripts/nexus_init.py
echo 'Starting API, Worker and Scheduler...'
dc up -d api worker scheduler
wait_healthy api 90
dc ps
echo 'PASS: Nexus is healthy. Demo usernames: teacher_a, student_a1, student_b1.'
echo "Passwords are stored only in the private $env_file."
