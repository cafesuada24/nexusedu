# Global Environment Rules
- **Python Manager**: Always use `uv`.
- **Execution**: Never run `python` or `python3` directly. Use `uv run python`.
- **Packages**: Use `uv add` instead of `pip install`.
- **Virtual Env**: Assume the environment is managed by `uv` in the `.venv` directory.
