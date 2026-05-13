.PHONY: generate_baml test lint start stop restart logs migrate makemigrations

start:
	@if [ ! -f .env ]; then cp .env.example .env; fi
	docker compose up --build -d

stop:
	docker compose down

restart: stop start

logs:
	docker compose logs -f

migrate:
	docker compose exec api alembic upgrade head

reset_db:
	./scripts/reset.sh

makemigrations:
	docker compose exec api alembic revision --autogenerate -m "$(m)"

test:
	PYTHONPATH=. uv run pytest tests/ -v

generate_baml:
	uv run baml generate --from ./src/infrastructure/extern/baml_src/

lint:
	uv run ruff check src/ --exclude ./src/infrastructure/extern/baml_client/ --fix


