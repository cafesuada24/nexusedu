"""Utility functions and classes for the agent assistant."""

import json
from collections.abc import Mapping
from typing import Any

import sqlglot
import yaml
from sqlglot import exp

from src.agents.state import MessageList, ResultList


class MessageSerializer:
    """Serializes message history for LLM prompts."""

    @staticmethod
    def to_yaml(messages: MessageList) -> str:
        """Convert a list of messages to a YAML-like XML format."""
        return '\n\n'.join(MessageSerializer._msg_to_yaml(msg) for msg in messages)

    @staticmethod
    def _msg_to_yaml(msg: Mapping[str, Any]) -> str:
        """Convert a single message to a YAML-like XML format."""
        # Handle LangChain message objects if they have 'type' and 'content'
        if hasattr(msg, 'type') and hasattr(msg, 'content'):
            role = 'ai_response' if getattr(msg, 'type') == 'ai' else 'human_message'
            content = getattr(msg, 'content')
        else:
            # Handle standard role/content dicts
            role = 'ai_response' if msg.get('role') == 'assistant' else 'human_message'
            content = msg.get('content', '')
        return f'<{role}>\n{content}\n</{role}>'


def mask_pii_sql(sql: str, pii_columns: set[str] | None = None) -> str:
    """Masks PII columns in a SQL query using AST manipulation for DuckDB.

    Uses sqlglot to parse, wrap in a subquery, and then transpile back to
    canonical DuckDB SQL to ensure no hidden payloads or breakout attempts.
    """
    if pii_columns is None:
        pii_columns = {'student_name', 'email', 'phone', 'student_email'}

    try:
        # 1. Parse into AST
        parsed = sqlglot.parse_one(sql, read='duckdb')

        # 2. Canonicalize the inner query first
        canonical_inner = parsed.sql(dialect='duckdb')
        reparsed_inner = sqlglot.parse_one(canonical_inner, read='duckdb')

        # 3. Wrap in a subquery
        subquery = reparsed_inner.subquery(alias='pii_masked_subquery')

        # 4. Build SELECT * EXCLUDE (...) from AST
        star = exp.Star(except_=[exp.column(c) for c in pii_columns])
        masked_query = sqlglot.select(star).from_(subquery)

        # 5. Transpile to final string
        return masked_query.sql(dialect='duckdb')
    except Exception as e:
        msg = f"Failed to parse SQL for PII masking: {e}"
        raise ValueError(msg) from e


def stringify_to_yaml(obj: object) -> str:
    """Convert an object or dict to indented YAML."""
    data = obj if isinstance(obj, dict) else vars(obj)
    dumped_yaml = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
    )
    return '\n'.join('  ' + line for line in dumped_yaml.splitlines())


class ResultSummarizer:
    """Summarizes query results for LLM context."""

    @staticmethod
    def summarize(results: ResultList, max_chars: int = 4000) -> str:
        """Summarize a list of database results."""
        summary: list[str] = []
        for res in results:
            db_id = res.get('db', 'unknown')
            data = res.get('data', [])

            # Handle error states from workers
            if isinstance(data, list) and len(data) > 0 and 'error' in data[0]:
                summary.append(f'Database: {db_id}\nError: {data[0]["error"]}\n')
                continue

            summary.append(f'Database: {db_id}')
            if isinstance(data, list):
                summary.append(f'Rows: {len(data)}')
                if len(data) > 0:
                    # Provide schema and a few sample rows
                    cols = list(data[0].keys()) if isinstance(data[0], dict) else 'N/A'
                    summary.append(f'Columns: {cols}')
                    sample_json = json.dumps(data[:2], indent=2, default=str)
                    summary.append(f'Sample: {sample_json}')
            summary.append('-' * 20)

        return '\n'.join(summary)[:max_chars]
