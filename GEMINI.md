# GEMINI.md - Project Context & Instructions

## Project Overview
**Name:** A20-App-007 (Agent Assistant)
**Type:** Python (3.11+) AI Agent Application
**Framework:** [LangGraph](https://github.com/langchain-ai/langgraph), [LangChain](https://github.com/langchain-ai/langchain)
**AI Models:** Primary use of Google Gemini (1.5 Flash/Pro) for orchestration and SQL generation.

### Purpose
This project is a template for building sophisticated AI agents that can:
1.  **Plan:** Interpret complex user intents (e.g., "Analyze student performance across all courses").
2.  **Execute:** Query multiple databases in parallel using dynamically generated SQL.
3.  **Process:** Aggregate results and decide on specialized next steps (Visualization, Email, Export).

---

## Architecture & Structure

### Core Workflow (`src/agent.py`)
The system implements a state-driven workflow via `langgraph.StateGraph`:
- **`planner`**: Identifies required tasks and databases using versioned prompts (`src/prompts/v1/planner.txt`).
- **`sql_worker`**: Parallelized nodes that generate and execute SQL queries against specific databases.
- **`determiner`**: Analyzes aggregated data and routes to downstream specialized agents.
- **`viz_agent` / `email_agent` / `export_agent`**: Downstream handlers for final data presentation and delivery.

### Key Directories
- `src/agents/`: State definitions (`state.py`), model initialization (`llms.py`), and planned node migrations.
- `src/prompts/`: Versioned system and task-specific prompt templates.
- `src/tools/`: Custom tools for database interactions (`db.py`), email (`email.py`), and data exporting.
- `scripts/`: Operational scripts for AI logging and git hooks.
- `models/`: Placeholder for local models (e.g., Whisper GGML).

---

## Building and Running

### 1. Environment Configuration
- **Initial Setup:** Run `bash scripts/setup_hooks.sh` to initialize AI logging and git pre-push hooks.
- **Variables:** `cp .env.example .env` and configure `ANTHROPIC_API_KEY` and `GOOGLE_API_KEY`.
- **Logging:** AI interactions are automatically logged to `.ai-log/` for telemetry.

### 2. Dependencies
- **Installation:** `pip install -r requirements.txt` or `uv sync`.
- **Key Packages:** `langchain-google-genai`, `langgraph`, `python-dotenv`, `ruff`.

### 3. Execution & Testing
- **Run Agent:** `python -m src.agent`
- **Linting/Formatting:** `ruff check .` and `ruff format .` (configured in `pyproject.toml`).
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
