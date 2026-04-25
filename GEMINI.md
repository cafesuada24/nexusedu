# GEMINI.md - Project Context & Instructions

## Project Overview
**Name:** A20-App-007 (Agent Assistant)
**Type:** Python (3.11+) AI Agent Application
**AI Models:** Primary use of Google Gemini (3.1 Flash/Pro) for orchestration and SQL generation.

### Purpose
This project is a template for building sophisticated AI agents that can:
1. Read multiple CSV files regarding students (from SIS, LMS systems), and understand the relationship between these files.
2. Analyze and detect 'anomalies' in user activities (such as a decline in scores, ignoring the quiz).
3. Write individualized supporting emails containing the booking link for help to those in trouble.

---

## Architecture & Structure

### Key Directories
- `src/agents/`: State definitions (`state.py`), model initialization (`llms.py`), and planned node migrations.
- `src/prompts/`: Versioned system and task-specific prompt templates.
- `scripts/`: Operational scripts for AI logging and git hooks.
- `models/`: Placeholder for local models (e.g., Whisper GGML).

---

## Building and Running

### 1. Environment Configuration
- **Initial Setup:** Run `bash scripts/setup_hooks.sh` to initialize AI logging and git pre-push hooks.
- **Variables:** `cp .env.example .env` and configure `ANTHROPIC_API_KEY` and `GOOGLE_API_KEY`.
- **Logging:** AI interactions are automatically logged to `.ai-log/` for telemetry.

### 2. Dependencies
- **Installation:** `uv pip install -r requirements.txt` or `uv sync`.

### 3. Execution & Testing
- **Run Agent:** `uv run python -m src.agent`
- **Linting/Formatting:** `uv run ruff check .` and `uv run ruff format .` (configured in `pyproject.toml`).
- **Testing:** `pytest` is the intended test runner (placeholder `test.py` exists).

---

## Development Conventions

### Documentation & Tracking
- **`JOURNAL.md`**: Mandatory weekly updates documenting product journey, AI tool usage, and learnings.
- **`WORKLOG.md`**: Record of technical decisions (ADRs), task assignments, and brainstorming.
- **`AGENTS.md`**: Specific rules and requirements for AI coding assistants (like Gemini CLI) interacting with this repo.

### Coding Style
- **Docstrings:** Use Google-style docstrings.
- **Type Hints:** Enforced for all function signatures (Python 3.11+ syntax).
- **Tooling:** Use `ruff` for all static analysis and formatting.

---

## Instructions for AI Agents
- **Logging:** Do not manually update prompt logs; it is handled automatically by the hooks in `scripts/`.
- **Pull Requests:** PRs must include a summary and a list of changed files. Ensure `setup_hooks.sh` has been run before finalizing any work.
- **Dependencies:** Verify usage of `langgraph` patterns (State, Nodes, Edges) before proposing architectural changes.
- **Coding**: always adhere to best practices in Python 3.12. Focus on optimization, scalable and fast prototyping.
- **Observability & Tracebility**: always implement the logging and monitoring components.
