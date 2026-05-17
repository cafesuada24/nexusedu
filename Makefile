# Default to development environment if not specified
ENV ?= dev

# Normalize ENV
ifeq ($(ENV),production)
    override ENV := prod
endif

# Define variables based on the environment
ifeq ($(ENV), prod)
    PROFILE = prod
    API_SVC = api
    ENV_FILE = .env
else
    PROFILE = dev
    API_SVC = api-dev
    ENV_FILE = .env
endif

.PHONY: generate_baml test lint start stop restart logs migrate makemigrations reset_db reseed

start:
	@if [ ! -f $(ENV_FILE) ]; then \
        if [ "$(ENV)" = "prod" ]; then \
            echo "Error: $(ENV_FILE) is missing. Please create it on the VM."; exit 1; \
        else \
            cp .env.example .env; \
        fi \
    fi
	docker compose --profile $(PROFILE) --env-file $(ENV_FILE) up --build -d

stop:
	docker compose --profile $(PROFILE) down

restart: stop start

logs:
	docker compose --profile $(PROFILE) logs -f

migrate:
	docker compose --profile $(PROFILE) exec $(API_SVC) alembic upgrade head

reseed:
	docker compose --profile $(PROFILE) exec $(API_SVC) env PYTHONPATH=. python scripts/reseed_dashboard.py

reset_db:
	./scripts/reset.sh $(ENV)

makemigrations:
	docker compose --profile $(PROFILE) exec $(API_SVC) alembic revision --autogenerate -m "$(m)"

test:
	PYTHONPATH=. uv run pytest tests/ -v

generate_baml:
	uv run baml generate --from ./src/infrastructure/extern/baml_src/

lint:
	uv run ruff check src/ --exclude ./src/infrastructure/extern/baml_client/ --fix
