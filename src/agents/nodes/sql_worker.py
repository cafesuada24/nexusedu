"""Node for generating and executing SQL queries."""

from typing import Any

from src.agents.state import SQLTask
from src.agents.utils import stringifyToYaml
from src.baml_client import b
from src.baml_client.types import GeneratedSQL
from src.telemetry.logger import logger
from src.tools.db import execute_sql, get_db_schema

MAX_LOOP = 3


def sql_worker(state: SQLTask) -> dict[str, Any]:
    """Node that generates and executes SQL for a specific database."""
    from src.api.lifecycle import get_dbmanager
    db_id = state['db_id']
    logger.info(f'SQL_Worker [{db_id}]: Starting task...')
    logger.debug(f'SQL_Worker [{db_id}] Intent: {state["query_intent"]}')

    # Proactive schema injection: fetch schema before first LLM call
    schema = get_db_schema(db_id, get_dbmanager())
    messages = [
        f'<task>\n{stringifyToYaml(state)}\n<\\task>',
        f'<db_schema_result>\ndb_id: {db_id}\n{schema}\n</db_schema_result>',
    ]
    sql_data = None
    raw_data = None
    for i in range(MAX_LOOP):
        sql_data = b.GenerateSQL('\n\n'.join(messages))
        if isinstance(sql_data, RequestDBSchema):
            logger.info(f'SQL_Worker [{db_id}]: LLM requested schema for {sql_data.db_id}')
            messages.append(
                f'<db_schema_request>\ndb_id: {sql_data.db_id}\n</db_schema_request>',
            )
            if sql_data.db_id == db_id:
                messages.append(
                    f'<db_schema_result>\ndb_id: {sql_data.db_id}\n{schema}\n</db_schema_result>',
                )
            else:
                new_schema = get_db_schema(sql_data.db_id, get_dbmanager())
                messages.append(
                    f'<db_schema_result>\ndb_id: {sql_data.db_id}\n{new_schema}\n</db_schema_result>',
                )
            continue

        # LLM generated SQL, now try to execute it
        logger.info(f'SQL_Worker [{db_id}]: Generated SQL: {sql_data.sql}')
        logger.log_event('sql_generated', sql_data.model_dump())

        try:
            logger.info(f'SQL_Worker [{db_id}]: Executing query (Attempt {i+1})...')
            raw_data = execute_sql(db_id, sql_data.sql, get_dbmanager())

            # Check for errors in the returned data if the tool returns a list with error dict
            if raw_data and isinstance(raw_data, list) and 'error' in raw_data[0]:
                error_msg = raw_data[0]['error']
                logger.warning(f'SQL_Worker [{db_id}]: Execution error: {error_msg}')
                messages.append(f'<sql_query>\n{sql_data.sql}\n</sql_query>')
                messages.append(f'<sql_error>\n{error_msg}\n</sql_error>')
                continue

            logger.info(f'SQL_Worker [{db_id}]: Execution successful. Rows: {len(raw_data)}')
            logger.log_event('sql_execution_success', {'db_id': db_id, 'rows': len(raw_data)})
            break
        except Exception as e:
            logger.error(f'Execution exception on {db_id}: {e}')
            messages.append(f'<sql_query>\n{sql_data.sql}\n</sql_query>')
            messages.append(f'<sql_error>\n{str(e)}\n</sql_error>')
            continue
    else:
        return {
            'results': [
                {
                    'db': db_id,
                    'data': {'error': f'Agent exceeded iteration limit {MAX_LOOP} or could not fix errors.'},
                },
            ],
        }

    return {
        'results': [{'db': db_id, 'data': raw_data}],
    }