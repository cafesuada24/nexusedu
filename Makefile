.PHONY: generate_baml run_dev test lint

run_dev:
	uv run uvicorn src.api.main:app --reload

test:
	PYTHONPATH=. uv run pytest tests/ -v

generate_baml:
	uv run baml generate --from ./src/baml_src

lint:
	uv run ruff check src/ --exclude src/baml_client

