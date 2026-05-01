"""Node for generating and executing SQL queries."""

from typing import TYPE_CHECKING, Any

import sqlglot
from langchain_core.runnables import RunnableConfig

from src.infrastructure.agents.state import SQLTask
from src.infrastructure.agents.utils import mask_pii_sql, stringify_to_yaml
from src.infrastructure.extern.baml_client import b
from src.infrastructure.extern.baml_client.types import RequestTableSchema
from src.telemetry.logger import logger

if TYPE_CHECKING:
    from src.application.services.agent_metadata import AgentMetadataService

MAX_LOOP = 3


class SQLWorkerNode:
    """Generates and executes SQL for a specific database."""

    async def __call__(self, state: SQLTask, config: RunnableConfig) -> dict[str, Any]:
        """Execute the SQL worker node."""
        metadata_service: AgentMetadataService | None = config.get(
            'configurable', {}
        ).get(
            'metadata_service',
        )
        if not metadata_service:
            logger.error('SQL_Worker: metadata_service not found in config')
            raise ValueError('metadata_service not found in config')

        db_id = state['db_id']
        logger.info(f'SQL_Worker [{db_id}]: Starting task...')
        logger.debug(f'SQL_Worker [{db_id}] Intent: {state["query_intent"]}')

        # Schema on Demand
        table_list = await metadata_service.get_formatted_table_list(db_id)
        task_prompt = f'<task>\n{stringify_to_yaml(state)}\n</task>'
        schema_context = [f'<available_tables>\n{table_list}\n</available_tables>']

        current_hint = ''
        raw_data = None

        for i in range(MAX_LOOP):
            raw_data, current_hint = await self._attempt_sql_execution(
                metadata_service=metadata_service,
                db_id=db_id,
                task_prompt=task_prompt,
                schema_context=schema_context,
                current_hint=current_hint,
                config=config,
                attempt=i,
            )
            if raw_data is not None and (
                not isinstance(raw_data, list)
                or not raw_data
                or 'error' not in raw_data[0]
            ):
                break
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

    async def _attempt_sql_execution(  # noqa: PLR0913
        self,
        *,
        metadata_service: 'AgentMetadataService',
        db_id: str,
        task_prompt: str,
        schema_context: list[str],
        current_hint: str,
        config: RunnableConfig,
        attempt: int,
    ) -> tuple[list[dict[str, Any]] | None, str]:
        """Attempt a single SQL generation and execution cycle."""
        prompt_parts = [task_prompt] + schema_context
        if current_hint:
            prompt_parts.append(f'<reflector_hint>\n{current_hint}\n</reflector_hint>')

        sql_data = b.GenerateSQL('\n\n'.join(prompt_parts))

        if isinstance(sql_data, RequestTableSchema):
            logger.info(
                f'SQL_Worker [{db_id}]: LLM requested schema for tables: {sql_data.table_names}',
            )
            for table_name in sql_data.table_names:
                table_schema = await metadata_service.get_formatted_table_schema(
                    sql_data.db_id,
                    table_name,
                )
                schema_context.append(
                    f'<table_schema name="{table_name}">\n{table_schema}\n</table_schema>',
                )
            return None, current_hint

        # LLM generated SQL, now try to execute it
        logger.info(f'SQL_Worker [{db_id}]: Generated SQL: {sql_data.sql}')
        logger.log_event('sql_generated', sql_data.model_dump())

        final_sql = self._sanitize_sql(sql_data.sql, config)

        try:
            logger.info(
                f'SQL_Worker [{db_id}]: Executing query (Attempt {attempt + 1})...',
            )
            raw_data = await metadata_service.execute(db_id, final_sql)

            if raw_data and isinstance(raw_data, list) and 'error' in raw_data[0]:
                error_msg = raw_data[0]['error']
                logger.warning(f'SQL_Worker [{db_id}]: Execution error: {error_msg}')
                hint = b.ReflectSQLError(
                    query=sql_data.sql,
                    error=error_msg,
                    db_schema_hint='\n'.join(schema_context),
                )
                return raw_data, str(hint)

            logger.info(
                f'SQL_Worker [{db_id}]: Execution successful. Rows: {len(raw_data)}',
            )
            return raw_data, ''
        except Exception as e:
            error_msg = str(e)
            logger.error(f'Execution exception on {db_id}: {error_msg}')
            hint = b.ReflectSQLError(
                query=sql_data.sql,
                error=error_msg,
                db_schema_hint='\n'.join(schema_context),
            )
            return [{'error': error_msg}], str(hint)

    def _sanitize_sql(self, sql: str, config: RunnableConfig) -> str:
        """Sanitize and transpile SQL, applying PII masking if needed.

        Args:
            sql: The raw SQL string to sanitize.
            config: The runnable configuration containing the user role.

        Returns:
            The sanitized and potentially masked SQL string.
        """
        try:
            # Note: transpile to DuckDB for now as existing prompt might expect it.
            # But the metadata service uses SQLite.
            # In a full unification, we'd eventually change the prompt or rely on SQLAlchemy.
            canonical_sql = sqlglot.transpile(sql, read='duckdb', write='duckdb')[0]
        except Exception as e:
            logger.warning(f'SQL_Worker: SQLGlot transpile failed: {e}. Using raw SQL.')
            canonical_sql = sql

        user_role = config.get('configurable', {}).get('user_role', 'viewer')
        if user_role == 'viewer':
            final_sql = mask_pii_sql(canonical_sql)
            logger.info('SQL_Worker: Applied PII masking')
            return final_sql

        return canonical_sql


sql_worker_node = SQLWorkerNode()
