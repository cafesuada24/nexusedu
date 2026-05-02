.PHONY: generate_baml test lint start stop restart

start:
	./scripts/manage_app.sh start

stop:
	./scripts/manage_app.sh stop

restart: stop start

run_dev: start

test:
	PYTHONPATH=. uv run pytest tests/ -v

generate_baml:
	uv run baml generate --from ./src/infrastructure/extern/baml_src/

lint:
	uv run ruff check src/ --exclude ./src/infrastructure/extern/baml_client/ --fix

run_redis:
	docker run -d --name arppool007 -p 6379:6379 redis


