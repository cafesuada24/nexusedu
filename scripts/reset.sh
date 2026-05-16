#!/usr/bin/env bash
# Reset the PostgreSQL database and seed initial data

set -e

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | sed 's/#.*//' | xargs)
fi

# Detect environment or default to dev
ENV_VAL=${ENVIRONMENT:-development}
ENV=${1:-$ENV_VAL}

# Normalize ENV
if [ "$ENV" = "production" ] || [ "$ENV" = "prod" ]; then
    ENV="prod"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "WARNING: YOU ARE ABOUT TO RESET THE PRODUCTION DATABASE!"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    read -p "Are you absolutely sure? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Reset cancelled."
        exit 1
    fi
    PROFILE="prod"
    API_SVC="api"
    WORKER_SVC="worker"
else
    ENV="dev"
    PROFILE="dev"
    API_SVC="api-dev"
    WORKER_SVC="worker-dev"
fi

# Determine DB target (prioritize cloud-sql-proxy if present, otherwise db)
DB_SERVICE=$(docker compose --profile "$PROFILE" ps --services 2>/dev/null | grep -q "^cloud-sql-proxy$" && echo "cloud-sql-proxy" || echo "db")

DB_USER=${POSTGRES_USER:-nexusedu_user}
DB_NAME=${POSTGRES_DB:-nexusedu}

echo "Stopping application services ($API_SVC, $WORKER_SVC)..."
docker compose --profile "$PROFILE" stop "$API_SVC" "$WORKER_SVC"

echo "Resetting PostgreSQL database: $DB_NAME using service: $DB_SERVICE (Env: $ENV)..."

# Function to execute psql commands based on the target service
run_psql() {
    if [ "$DB_SERVICE" = "db" ]; then
        docker compose --profile "$PROFILE" exec -T "$DB_SERVICE" psql -U "$DB_USER" -d "$1" -c "$2"
    else
        docker compose --profile "$PROFILE" run --rm -T --no-deps \
            -e DB_SERVICE_HOST="$DB_SERVICE" \
            -e DB_USER="$DB_USER" \
            -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
            "$API_SVC" \
            python -c '
import psycopg, os, sys
try:
    conn = psycopg.connect(
        host=os.environ.get("DB_SERVICE_HOST"),
        dbname=sys.argv[1],
        user=os.environ.get("DB_USER"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
        autocommit=True
    )
    conn.execute(sys.argv[2])
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
' "$1" "$2"
    fi
}

# Terminate connections
run_psql postgres "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" || true

# Drop and recreate
run_psql postgres "DROP DATABASE IF EXISTS $DB_NAME;"
run_psql postgres "CREATE DATABASE $DB_NAME;"

echo "Starting application services..."
docker compose --profile "$PROFILE" start "$API_SVC" "$WORKER_SVC"

echo "Running migrations..."
make migrate ENV="$ENV"

echo "Seeding default users..."
# Inside the container, the venv is already in the PATH and uv is not present in the runtime image.
docker compose --profile "$PROFILE" exec -T "$API_SVC" env PYTHONPATH=. python scripts/create_user.py --email dev@gmail.com --password dev --role admin
docker compose --profile "$PROFILE" exec -T "$API_SVC" env PYTHONPATH=. python scripts/create_user.py --email adv@gmail.com --password adv --role advisor

echo "Database reset successfully."
