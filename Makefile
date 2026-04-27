.PHONY: generate_baml run_dev

run_dev:
	uv run uvicorn src.api.main:app --reload

test:
	PYTHONPATH=. uv run pytest tests/ -v

generate_baml:
	uv run baml generate --from ./src/baml_src

