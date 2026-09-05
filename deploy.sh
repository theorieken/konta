#!/usr/bin/env bash
# =============================================================================
# Haushalts-Finanzplanung – one command deployment.
#
#   bash deploy.sh              build + start everything, run migrations, seed
#   bash deploy.sh --rebuild    force a clean image rebuild (no cache)
#   bash deploy.sh --logs       start and then follow the logs
#   bash deploy.sh --down       stop the stack (keeps volumes/data)
#   bash deploy.sh --reset      stop the stack AND delete all data volumes
#
# Running this without a .env creates one from .env.example and generates
# secrets, so a fresh clone always ends up with a working platform.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; GREEN=$'\033[32m'
YELLOW=$'\033[33m'; BLUE=$'\033[34m'; RESET=$'\033[0m'

info()  { printf '%s\n' "${BLUE}▸${RESET} $*"; }
ok()    { printf '%s\n' "${GREEN}✓${RESET} $*"; }
warn()  { printf '%s\n' "${YELLOW}!${RESET} $*"; }
fail()  { printf '%s\n' "${RED}✗${RESET} $*" >&2; exit 1; }
step()  { printf '\n%s\n' "${BOLD}$*${RESET}"; }

REBUILD=0
FOLLOW_LOGS=0
ACTION="up"

for arg in "$@"; do
  case "$arg" in
    --rebuild) REBUILD=1 ;;
    --logs)    FOLLOW_LOGS=1 ;;
    --down)    ACTION="down" ;;
    --reset)   ACTION="reset" ;;
    -h|--help) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)         fail "Unknown option: $arg (try --help)" ;;
  esac
done

# -----------------------------------------------------------------------------
# 1. Requirements
# -----------------------------------------------------------------------------
step "1/6  Voraussetzungen prüfen"

command -v docker >/dev/null 2>&1 || fail "Docker ist nicht installiert. https://docs.docker.com/get-docker/"

if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
else
  fail "Docker Compose fehlt. Bitte Docker Desktop oder das compose-Plugin installieren."
fi

docker info >/dev/null 2>&1 || fail "Docker läuft nicht. Bitte Docker starten und erneut versuchen."
ok "Docker und Compose sind einsatzbereit ($DC)"

# -----------------------------------------------------------------------------
# 2. Environment
# -----------------------------------------------------------------------------
step "2/6  Konfiguration vorbereiten"

random_secret() {
  # 48 url-safe characters, works without python/openssl being present.
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 48 | tr -d '\n=+/' | cut -c1-48
  else
    LC_ALL=C tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 48
  fi
}

if [ ! -f .env ]; then
  cp .env.example .env
  ok ".env aus .env.example erstellt"
else
  ok "Vorhandene .env wird verwendet"
  # Make sure keys added by newer versions are present in an older .env.
  while IFS= read -r line; do
    case "$line" in
      ''|\#*) continue ;;
    esac
    key="${line%%=*}"
    if ! grep -q "^${key}=" .env; then
      printf '%s\n' "$line" >> .env
      warn "Neuer Konfigurationswert ergänzt: ${key}"
    fi
  done < .env.example
fi

# Replace placeholder secrets so a default deployment is never insecure by accident.
replace_placeholder() {
  local key="$1"
  if grep -q "^${key}=CHANGE_ME" .env; then
    local value; value="$(random_secret)"
    # portable in-place edit (BSD + GNU sed)
    sed "s|^${key}=.*|${key}=${value}|" .env > .env.tmp && mv .env.tmp .env
    ok "${key} generiert"
  fi
}
replace_placeholder DJANGO_SECRET_KEY
replace_placeholder SECURITY_SALT

# Load the env for this script (URLs, ports, ...). Values are also read by compose.
set -a
# shellcheck disable=SC1091
. ./.env
set +a

SCHEME="${SCHEME:-http}"
DOMAIN="${DOMAIN:-localhost}"
PORT="${PORT:-8080}"

# The stack only needs one host port. If it is taken by something else we pick
# the next free one and remember it, so a fresh deploy never dies on a clash.
port_in_use() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1 && return 0
    return 1
  fi
  if command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 "$1" >/dev/null 2>&1 && return 0
    return 1
  fi
  return 1
}

if port_in_use "$PORT"; then
  candidate="$PORT"
  attempts=0
  while port_in_use "$candidate" && [ "$attempts" -lt 50 ]; do
    candidate=$((candidate + 1))
    attempts=$((attempts + 1))
  done
  if [ "$candidate" != "$PORT" ] && ! port_in_use "$candidate"; then
    warn "Port ${PORT} ist belegt – die App läuft stattdessen auf Port ${candidate}."
    warn "Zum Festlegen: PORT in der .env anpassen."
    sed "s|^PORT=.*|PORT=${candidate}|" .env > .env.tmp && mv .env.tmp .env
    PORT="$candidate"
    export PORT
  else
    fail "Port ${PORT} ist belegt und es wurde kein freier Port gefunden. Bitte PORT in der .env setzen."
  fi
fi

APP_URL="${SCHEME}://${DOMAIN}:${PORT}"
[ "$PORT" = "80" ] && APP_URL="${SCHEME}://${DOMAIN}"

# -----------------------------------------------------------------------------
# 3. down / reset shortcuts
# -----------------------------------------------------------------------------
if [ "$ACTION" = "down" ]; then
  step "Stack stoppen"
  $DC down
  ok "Gestoppt. Daten bleiben erhalten."
  exit 0
fi

if [ "$ACTION" = "reset" ]; then
  step "Stack stoppen und ALLE Daten löschen"
  printf '%s' "${YELLOW}Wirklich alle Datenbank-, Redis- und MinIO-Daten löschen? [j/N] ${RESET}"
  read -r answer
  case "$answer" in
    j|J|y|Y) $DC down -v; ok "Stack und Volumes entfernt." ;;
    *)       warn "Abgebrochen."; ;;
  esac
  exit 0
fi

# -----------------------------------------------------------------------------
# 4. Build
# -----------------------------------------------------------------------------
step "3/6  Images bauen"
if [ "$REBUILD" = "1" ]; then
  $DC build --no-cache
else
  $DC build
fi
ok "Images gebaut"

# -----------------------------------------------------------------------------
# 5. Start
# -----------------------------------------------------------------------------
step "4/6  Container starten"
$DC up -d --remove-orphans
ok "Container gestartet"

# -----------------------------------------------------------------------------
# 6. Wait for health
# -----------------------------------------------------------------------------
step "5/6  Auf das Backend warten"
# The backend entrypoint runs migrations + seeding before it reports healthy.
deadline=$(( $(date +%s) + 300 ))
healthy=0
while [ "$(date +%s)" -lt "$deadline" ]; do
  status="$($DC ps --format json backend 2>/dev/null | tr ',' '\n' | grep -o '"Health":"[a-z]*"' | head -1 | cut -d'"' -f4 || true)"
  if [ "$status" = "healthy" ]; then healthy=1; break; fi
  if [ "$status" = "unhealthy" ]; then break; fi
  printf '%s' "${DIM}.${RESET}"
  sleep 3
done
printf '\n'

if [ "$healthy" != "1" ]; then
  warn "Backend meldet sich nicht als 'healthy'. Letzte Logzeilen:"
  $DC logs --tail=60 backend || true
  fail "Deployment unvollständig. Details siehe oben, danach 'bash deploy.sh' erneut ausführen."
fi
ok "Backend ist bereit (Migrationen + Seed abgeschlossen)"

step "6/6  Frontend prüfen"
deadline=$(( $(date +%s) + 180 ))
until curl -fsS -o /dev/null "${APP_URL}/" 2>/dev/null; do
  if [ "$(date +%s)" -ge "$deadline" ]; then
    warn "Frontend antwortet noch nicht auf ${APP_URL}. Logs:"
    $DC logs --tail=40 frontend nginx || true
    break
  fi
  printf '%s' "${DIM}.${RESET}"
  sleep 3
done
printf '\n'
ok "Frontend erreichbar"

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
cat <<SUMMARY

${GREEN}${BOLD}Die Finanzplanung läuft.${RESET}

  ${BOLD}App${RESET}            ${APP_URL}
  ${BOLD}API${RESET}            ${APP_URL}/api/
  ${BOLD}API-Doku${RESET}       ${APP_URL}/api/docs/
  ${BOLD}Django Admin${RESET}   ${APP_URL}/admin/
  ${BOLD}Dateien${RESET}        ${APP_URL}/s3/  ${DIM}(MinIO über nginx)${RESET}

  ${DIM}Beim ersten Aufruf führt die App durch das Onboarding und legt
  den ersten Benutzer, die Konten und die Standardkategorien an.${RESET}

  Logs        ${DIM}${DC} logs -f backend celery-worker${RESET}
  Stoppen     ${DIM}bash deploy.sh --down${RESET}
  Zurücksetzen${DIM} bash deploy.sh --reset${RESET}

SUMMARY

if [ "$FOLLOW_LOGS" = "1" ]; then
  $DC logs -f
fi
