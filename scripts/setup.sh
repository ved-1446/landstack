#!/usr/bin/env bash
# One-command setup for LandStack on Linux and macOS (Windows PowerShell: scripts/setup.ps1).
#
#   bash scripts/setup.sh [--yes] [--skip-corpus] [--skip-frontend]
#
# Steps: check tools -> .env -> start the database (Docker) -> Python packages -> create the schema -> seed the fake data
#        -> seed the demo users -> build the Land Guide corpus -> run the checks -> install the web app packages.
#
# It will NOT, without telling you:
#   * Applying db/schema.sql DROPS and recreates every table (demo data, users, audit log, issued-passport records).
#     If the database already has tables, it stops and asks first. --yes answers "yes".
#   * POSTGRES_PORT and LANDSTACK_DB_CONTAINER from your environment are written into a NEW .env (use them if 5432 or "landstack-db" is taken).
#   * It never overwrites an existing .env, never prints a secret and never runs git commit.
# The Land Guide step downloads 6 public pages politely (about 30 seconds). --skip-corpus skips the download.
set -euo pipefail

YES=0; SKIP_CORPUS=0; SKIP_FRONTEND=0
for arg in "$@"; do
  case "$arg" in
    --yes) YES=1 ;; --skip-corpus) SKIP_CORPUS=1 ;; --skip-frontend) SKIP_FRONTEND=1 ;;
    *) echo "Unknown option: $arg"; exit 2 ;;
  esac
done

cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT="$(pwd)"
step() { printf '\n[%s] %s\n' "$1" "$2"; }
fail() { echo "STOPPED: $1" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "$1 was not found. $2"; }
random_text() { LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c "$1"; }
env_value() {   # env_value NAME DEFAULT
  local v; v="$(grep -E "^[[:space:]]*$1[[:space:]]*=" .env 2>/dev/null | head -n1 | cut -d= -f2- | tr -d '\r' | xargs || true)"
  echo "${v:-$2}"
}

step 1 "Checking tools"
need docker "Install Docker and start it."
need python3 "Install Python 3.14 (what the pinned versions were tested on; 3.11 to 3.13 may work)."
docker info >/dev/null 2>&1 || fail "Docker is installed but not running. Start it and run this again."
[ "$SKIP_FRONTEND" = 1 ] || need npm "Install Node.js 20.19 or newer (24 was tested), or use --skip-frontend."

step 2 "Checking .env"
if [ ! -f .env ]; then
  umask 077
  cat > .env <<EOF
# Made by scripts/setup.sh. Never commit this file (it is git-ignored).
POSTGRES_USER=landstack
POSTGRES_PASSWORD=$(random_text 32)
POSTGRES_DB=landstack
POSTGRES_HOST=localhost
$( [ -n "${LANDSTACK_DB_CONTAINER:-}" ] && echo "LANDSTACK_DB_CONTAINER=$LANDSTACK_DB_CONTAINER" )
POSTGRES_PORT=${POSTGRES_PORT:-5432}
JWT_SECRET=$(random_text 64)
JWT_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:5173
PUBLIC_BASE_URL=http://localhost:8000
OPENROUTER_API_KEY=
OPENROUTER_MODEL=
EOF
  echo "Created .env with a random database password and a random login secret (values not shown)."
else
  echo ".env already exists and is left alone."
  for k in POSTGRES_PASSWORD JWT_SECRET; do
    grep -Eq "^[[:space:]]*$k[[:space:]]*=[[:space:]]*[^[:space:]]" .env || fail "$k is missing or empty in .env. Add it (see .env.example), then run this again."
  done
fi
USER_NAME="$(env_value POSTGRES_USER landstack)"; DB_NAME="$(env_value POSTGRES_DB landstack)"
CONTAINER="$(env_value LANDSTACK_DB_CONTAINER landstack-db)"

step 3 "Starting the database (Docker, PostGIS)"
if docker ps -a --format "{{.Names}}" 2>/dev/null | grep -qx "landstack-db" && [ "$CONTAINER" != "landstack-db" ]; then
  echo "Note: an OLD container named landstack-db exists (from before the rename). It is left alone; this script starts $CONTAINER with a new, empty database. Remove the old one yourself when you no longer need it."
fi
docker compose up -d || fail "docker compose up failed. If the name or port is taken, set LANDSTACK_DB_CONTAINER or POSTGRES_PORT in .env."
ready=0
for _ in $(seq 1 60); do
  if docker exec "$CONTAINER" pg_isready -U "$USER_NAME" -d "$DB_NAME" >/dev/null 2>&1; then ready=1; break; fi
  sleep 2
done
[ "$ready" = 1 ] || fail "the database did not become ready in 2 minutes. Look at: docker logs $CONTAINER"
echo "Database is ready."

step 4 "Python environment and packages"
[ -d .venv ] || python3 -m venv .venv || fail "could not create .venv"
PY="$ROOT/.venv/bin/python"
"$PY" -m pip install --quiet --disable-pip-version-check -r backend/requirements.txt \
  || fail "pip install failed (the pinned versions were tested on Python 3.14; an older Python may lack a wheel)."

step 5 "Creating the schema"
has="$(docker exec "$CONTAINER" psql -U "$USER_NAME" -d "$DB_NAME" -tAc "SELECT to_regclass('public.plots') IS NOT NULL" | tr -d '[:space:]')"
if [ "$has" = "t" ]; then
  echo "The database already has LandStack tables. Applying the schema DROPS and recreates every table:"
  echo "  all plots, demo users, the audit log and issued-passport records will be deleted (they are rebuilt by the next steps)."
  if [ "$YES" != 1 ]; then
    read -r -p "Type YES to continue (anything else stops here): " answer
    [ "$answer" = "YES" ] || fail "left the existing tables untouched, as you asked."
  fi
fi
docker exec -i "$CONTAINER" psql -U "$USER_NAME" -d "$DB_NAME" -v ON_ERROR_STOP=1 -q < db/schema.sql || fail "applying db/schema.sql failed."

step 6 "Seeding the fake data (fixed seed: same data every time) and the demo users"
"$PY" db/seed.py || fail "db/seed.py failed."
"$PY" db/seed_users.py || fail "db/seed_users.py failed."

step 7 "Building the Land Guide corpus"
if [ "$SKIP_CORPUS" = 1 ]; then "$PY" -m chatbot.build --index-only || true
else echo "(Downloads 6 public pages politely, 4 seconds apart. Skip with --skip-corpus.)"; "$PY" -m chatbot.build \
  || echo "The corpus step had a problem. The Land Guide still works from its glossary. Continuing."; fi

step 8 "Running the checks (flagged problems against the planted ones)"
"$PY" -m backend.app.checks || fail "the checks failed."

if [ "$SKIP_FRONTEND" != 1 ]; then
  step 9 "Installing the web app packages"
  (cd frontend && npm ci --no-audit --no-fund) || fail "npm ci failed."
  if [ ! -f frontend/.env ]; then
    echo "VITE_DEMO_ACCOUNTS=true" > frontend/.env
    echo "Created frontend/.env with VITE_DEMO_ACCOUNTS=true (shows the demo login buttons; use false in any real deployment)."
  fi
fi

printf '\nDone. To run it, open two terminals in %s :\n' "$ROOT"
echo "  1)  .venv/bin/python -m uvicorn backend.app.main:app --reload"
echo "  2)  cd frontend && npm run dev        then open http://localhost:5173"
echo "Demo logins and the 6-click tour: docs/DEMO.md"
