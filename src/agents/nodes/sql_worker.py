"""Node for generating and executing SQL queries."""

from typing import Any

from langchain_core.runnables import RunnableConfig

from src.agents.state import SQLTask
from src.agents.utils import stringifyToYaml
from src.baml_client import b
from src.baml_client.types import RequestTableSchema
from src.telemetry.logger import logger

MAX_LOOP = 3


def sql_worker(state: SQLTask, config: RunnableConfig) -> dict[str, Any]:
    """Node that generates and executes SQL for a specific database."""
    # Extract db_manager from config
    db_manager = config.get('configurable', {}).get('db_manager')
    if not db_manager:
        logger.error('SQL_Worker: db_manager not found in config')
        raise ValueError('db_manager not found in config')

    db_id = state['db_id']
    logger.info(f'SQL_Worker [{db_id}]: Starting task...')
    logger.debug(f'SQL_Worker [{db_id}] Intent: {state["query_intent"]}')

    # Schema on Demand: initially only inject table list to keep context small
    table_list = db_manager.get_formatted_table_list(db_id)
    task_prompt = f'<task>\n{stringifyToYaml(state)}\n</task>'
    schema_context = [f'<available_tables>\n{table_list}\n</available_tables>']

    # We maintain a list of messages for the LLM.
    # In each retry, we rebuild it to avoid history bloat.
    current_hint = ''

    raw_data = None
    for i in range(MAX_LOOP):
        prompt_parts = [task_prompt] + schema_context
        if current_hint:
            prompt_parts.append(f'<reflector_hint>\n{current_hint}\n</reflector_hint>')

        sql_data = b.GenerateSQL('\n\n'.join(prompt_parts))

        if isinstance(sql_data, RequestTableSchema):
            logger.info(
                f'SQL_Worker [{db_id}]: LLM requested schema for tables: {sql_data.table_names}',
            )
            for table_name in sql_data.table_names:
                table_schema = db_manager.get_formatted_table_schema(
                    sql_data.db_id, table_name,
                )
                schema_context.append(
                    f'<table_schema name="{table_name}">\n{table_schema}\n</table_schema>',
                )
            # Don't increment i for schema requests if we want to give it more chances,
            # but for now we follow MAX_LOOP as safety.
            continue

        # LLM generated SQL, now try to execute it
        logger.info(f'SQL_Worker [{db_id}]: Generated SQL: {sql_data.sql}')
        logger.log_event('sql_generated', sql_data.model_dump())

        try:
            logger.info(f'SQL_Worker [{db_id}]: Executing query (Attempt {i + 1})...')
            raw_data = db_manager.execute(db_id, sql_data.sql)

            # Check for errors in the returned data if the tool returns a list with error dict
            if raw_data and isinstance(raw_data, list) and 'error' in raw_data[0]:
                error_msg = raw_data[0]['error']
                logger.warning(f'SQL_Worker [{db_id}]: Execution error: {error_msg}')

                # Surgical Reflector: call BAML to get a concise hint
                current_hint = b.ReflectSQLError(
                    query=sql_data.sql,
                    error=error_msg,
                    db_schema_hint='\n'.join(schema_context),
                )
                logger.info(f'SQL_Worker [{db_id}]: Reflector Hint: {current_hint}')
                continue

            logger.info(
                f'SQL_Worker [{db_id}]: Execution successful. Rows: {len(raw_data)}',
            )
            logger.log_event(
                'sql_execution_success',
                {'db_id': db_id, 'rows': len(raw_data)},
            )
            break
        except Exception as e:
            error_msg = str(e)
            logger.error(f'Execution exception on {db_id}: {error_msg}')
            current_hint = b.ReflectSQLError(
                query=sql_data.sql,
                error=error_msg,
                db_schema_hint='\n'.join(schema_context),
            )
            logger.info(f'SQL_Worker [{db_id}]: Reflector Hint: {current_hint}')
            continue
    else:
        return {
            'results': [
                {
                    'db': db_id,
                    'data': {
                        'error': f'Agent exceeded iteration limit {MAX_LOOP} or could not fix errors.',
                    },
                },
            ],
        }

    return {
        'results': [{'db': db_id, 'data': raw_data}],
    }
