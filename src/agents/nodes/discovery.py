"""Node that performs schema discovery using database tools."""

from typing import Any

from langchain_core.runnables import RunnableConfig

from src.agents.state import AgentState
from src.telemetry.logger import logger
from src.tools.db import (
    describe_table,
    get_db_list,
    list_tables,
)


def discovery_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """Node that performs schema discovery using database tools."""
    logger.info('Discovery: Executing tools...')
    routing = state.get('routing_metadata', {})
    discovery_requests = routing.get('discovery_requests') or []
    new_context_parts: list[str] = []

    # Extract db_manager from config
    db_manager = config.get('configurable', {}).get('db_manager')
    if not db_manager:
        logger.error('Discovery: db_manager not found in config')
        raise ValueError('db_manager not found in config')

    logger.info(f'Discovery: Processing {len(discovery_requests)} requests')

    for i, req in enumerate(discovery_requests):
        # Safely extract fields whether req is a dict or a Pydantic model
        if isinstance(req, dict):
            tool_name = req.get('tool_name')
            db_id = req.get('db_id')
            table_name = req.get('table_name')
        else:
            tool_name = getattr(req, 'tool_name', None)
            db_id = getattr(req, 'db_id', None)
            table_name = getattr(req, 'table_name', None)

        if tool_name == 'get_db_list':
            res = get_db_list()
        elif tool_name == 'list_tables' and db_id:
            res = list_tables(db_id=db_id, db_manager=db_manager)
        elif tool_name == 'describe_table' and db_id and table_name:
            res = describe_table(db_id=db_id, table_name=table_name, db_manager=db_manager)
        else:
            logger.warning(f'Discovery Task {i + 1}: Unknown tool {tool_name} or missing args')
            continue

        logger.info(
            f'Discovery Task {i + 1}: Calling {tool_name} for {db_id or "root"}/{table_name or "none"}',
        )

        try:
            if res:
                new_context_parts.append(str(res))
                logger.debug(f'Discovery Task {i + 1} Result length: {len(str(res))}')
        except Exception as e:
            logger.error(
                f'Discovery Task {i + 1} ({tool_name}) failed: {e}',
                exc_info=True,
            )

    current_context = state.get('discovery_context') or ''
    updated_context = current_context + '\n\n' + '\n\n'.join(new_context_parts)

    logger.info(f'Discovery: Updated context length: {len(updated_context)}')

    return {
        'discovery_context': updated_context,
        'routing_metadata': {
            **routing,
            'discovery_requests': [],
        },
    }
