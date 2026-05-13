#!/usr/bin/env bash
# Reset the PostgreSQL database and seed initial data

set -e

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | sed 's/#.*//' | xargs)
fi

DB_USER=${POSTGRES_USER:-myuser}
DB_NAME=${POSTGRES_DB:-a20app}

echo "Stopping application services to close connections..."
docker compose stop api worker

echo "Resetting PostgreSQL database: $DB_NAME..."
# Terminate other connections if any (just in case)
docker compose exec -T db psql -U "$DB_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" || true
# Drop and recreate
docker compose exec -T db psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
docker compose exec -T db psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"

echo "Starting application services..."
docker compose start api worker

# Give services a moment to start
echo "Waiting for database to be ready..."
until docker compose exec -T db pg_isready -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; do
  sleep 1
done

echo "Running migrations..."
make migrate

echo "Seeding default users..."
# Run seeding inside the container
docker compose exec api env PYTHONPATH=. python scripts/create_user.py --email dev@gmail.com --password dev --role admin
docker compose exec api env PYTHONPATH=. python scripts/create_user.py --email adv@gmail.com --password adv --role advisor

echo "Database reset successfully."
