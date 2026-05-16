#!/usr/bin/env bash
# Reset the PostgreSQL database and seed initial data

set -e

# Detect environment or default to dev
ENV=${1:-dev}
PROFILE=$([ "$ENV" = "prod" ] && echo "prod" || echo "dev")
API_SVC=$([ "$ENV" = "prod" ] && echo "api" || echo "api-dev")

# Determine DB target (prioritize cloud-sql-proxy if present, otherwise db)
DB_SERVICE=$(docker compose --profile "$PROFILE" ps --services | grep -q "^cloud-sql-proxy$" && echo "cloud-sql-proxy" || echo "db")

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | sed 's/#.*//' | xargs)
fi

DB_USER=${POSTGRES_USER:-nexusedu_user}
DB_NAME=${POSTGRES_DB:-nexusedu}

echo "Stopping application services..."
docker compose --profile "$PROFILE" stop "$API_SVC"

echo "Resetting PostgreSQL database: $DB_NAME using service: $DB_SERVICE..."

# Function to execute psql commands based on the target service
run_psql() {
    docker compose --profile "$PROFILE" exec -T "$DB_SERVICE" psql -U "$DB_USER" -d "$1" -c "$2"
}

# Terminate connections
run_psql postgres "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" || true

# Drop and recreate
run_psql postgres "DROP DATABASE IF EXISTS $DB_NAME;"
run_psql postgres "CREATE DATABASE $DB_NAME;"

echo "Starting application services..."
docker compose --profile "$PROFILE" start "$API_SVC"

echo "Running migrations..."
make migrate ENV="$ENV"

echo "Seeding default users..."
docker compose --profile "$PROFILE" exec -T "$API_SVC" env PYTHONPATH=. python scripts/create_user.py --email dev@gmail.com --password dev --role admin
docker compose --profile "$PROFILE" exec -T "$API_SVC" env PYTHONPATH=. python scripts/create_user.py --email adv@gmail.com --password adv --role advisor

echo "Database reset successfully."
