#!/usr/bin/env bash
# Single entrypoint for every backend role. The first argument selects the role:
#   asgi    -> daphne ASGI server (REST + WebSockets); also runs migrations/seed
#   worker  -> celery worker
#   beat    -> celery beat scheduler
#   shell   -> interactive shell for debugging
set -euo pipefail

ROLE="${1:-asgi}"

wait_for() {
  local host="$1" port="$2" label="$3" tries=60
  echo "→ warte auf ${label} (${host}:${port})"
  until python -c "import socket,sys; s=socket.socket(); s.settimeout(2); sys.exit(0 if s.connect_ex(('${host}', ${port}))==0 else 1)"; do
    tries=$((tries - 1))
    [ "$tries" -le 0 ] && { echo "✗ ${label} nicht erreichbar"; exit 1; }
    sleep 2
  done
  echo "✓ ${label} erreichbar"
}

wait_for "${POSTGRES_HOST:-postgres}" "${POSTGRES_PORT:-5432}" "PostgreSQL"
wait_for "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" "Redis"

case "$ROLE" in
  asgi)
    echo "→ Migrationen anwenden"
    python manage.py migrate --noinput
    echo "→ Statische Dateien sammeln"
    python manage.py collectstatic --noinput --clear >/dev/null
    echo "→ Standarddaten anlegen"
    python manage.py seed_defaults
    echo "→ Periodische Aufgaben registrieren"
    python manage.py setup_periodic_tasks
    echo "→ Daphne startet auf 0.0.0.0:8000"
    exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
    ;;
  worker)
    exec celery -A config worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-2}"
    ;;
  beat)
    exec celery -A config beat --loglevel=info \
      --scheduler django_celery_beat.schedulers:DatabaseScheduler
    ;;
  shell)
    exec python manage.py shell
    ;;
  *)
    exec "$@"
    ;;
esac
