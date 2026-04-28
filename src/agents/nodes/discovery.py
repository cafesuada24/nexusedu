"""Node that performs schema discovery using database tools."""

from typing import Any

from langchain_core.runnables import RunnableConfig

from src.agents.state import AgentState
from src.telemetry.logger import logger

MAX_DISCOVERY_CONTEXT_CHARS = 15_000


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

        match tool_name:
            case 'get_db_list':
                res = db_manager.get_formatted_db_list()
            case 'list_tables' if db_id:
                res = db_manager.get_formatted_table_list(db_id=db_id)
            case 'describe_table' if db_id and table_name:
                res = db_manager.get_formatted_table_schema(
                    db_id=db_id, table_name=table_name,
                )
            case _:
                logger.warning(
                    f'Discovery Task {i + 1}: Unknown tool {tool_name} or missing args',
                )
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

    # Prevent unbounded growth of discovery_context
    if len(updated_context) > MAX_DISCOVERY_CONTEXT_CHARS:
        logger.warning(
            f'Discovery: Context limit reached ({len(updated_context)} > {MAX_DISCOVERY_CONTEXT_CHARS}). Truncating...',
        )
        updated_context = updated_context[-MAX_DISCOVERY_CONTEXT_CHARS:]

    logger.info(f'Discovery: Updated context length: {len(updated_context)}')

    return {
        'discovery_context': updated_context,
        'discovery_depth': state.get('discovery_depth', 0) + 1,
        'routing_metadata': {
            **routing,
            'discovery_requests': [],
        },
    }
