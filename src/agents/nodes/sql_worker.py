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
    db_id = state['db_id']
    logger.info(f'SQL_Worker [{db_id}]: Starting task...')
    logger.debug(f'SQL_Worker [{db_id}] Intent: {state["query_intent"]}')

    messages = [f'<task>\n{stringifyToYaml(state)}\n<\\task>']
    sql_data = None
    for _ in range(MAX_LOOP):
        sql_data = b.GenerateSQL('\n\n'.join(messages))
        if isinstance(sql_data, GeneratedSQL):
            logger.info(f'SQL_Worker [{db_id}]: Generated SQL: {sql_data.sql}')
            logger.log_event('sql_generated', sql_data.model_dump())
            break
        messages.append(
            f'<db_schema_request>\ndb_id: {sql_data.db_id}\n</db_schema_request>',
        )
        schema = get_db_schema(sql_data.db_id)
        messages.append(
            f'<db_schema_result>\ndb_id: {sql_data.db_id}\n{schema}\n</db_schema_result>',
        )
    else:
        return {
            'results': [
                {
                    'db': db_id,
                    'data': {'error': f'Agent exceeded iteration limit {MAX_LOOP}'},
                },
            ],
        }

    try:
        logger.info(f'SQL_Worker [{db_id}]: Executing query...')
        raw_data = execute_sql(db_id, sql_data.sql)
        logger.info(
            f'SQL_Worker [{db_id}]: Execution successful. Rows: {len(raw_data)}',
        )
        logger.log_event(
            'sql_execution_success',
            {'db_id': db_id, 'rows': len(raw_data)},
        )
    except Exception as e:
        logger.error(f'Execution error on {db_id}: {e}', exc_info=True)
        raw_data = [{'error': str(e)}]
        logger.log_event('sql_execution_error', {'db_id': db_id, 'error': str(e)})

    return {
        'results': [{'db': db_id, 'data': raw_data}],
    }
