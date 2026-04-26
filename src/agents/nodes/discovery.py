"""Node that performs schema discovery using database tools."""

from collections.abc import Callable
from typing import Any

from src.agents.state import AgentState
from src.telemetry.logger import logger
from src.tools.db import (
    describe_table,
    get_db_list,
    list_tables,
)

# Tool Dispatch Map
DISCOVERY_TOOLS: dict[str, Callable[[dict[str, Any]], Any]] = {
    'get_db_list': lambda _: get_db_list.invoke({}),
    'list_tables': lambda args: list_tables.invoke({'db_id': args.get('db_id')})
    if args.get('db_id')
    else None,
    'describe_table': lambda args: describe_table.invoke(
        {'db_id': args.get('db_id'), 'table_name': args.get('table_name')},
    )
    if args.get('db_id') and args.get('table_name')
    else None,
}


def discovery_node(state: AgentState) -> dict[str, Any]:
    """Node that performs schema discovery using database tools."""
    logger.info('Discovery: Executing tools...')
    routing = state.get('routing_metadata', {})
    discovery_requests = routing.get('discovery_requests') or []
    new_context_parts: list[str] = []

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

        args = {
            'db_id': db_id,
            'table_name': table_name,
        }

        if tool_name not in DISCOVERY_TOOLS:
            logger.warning(f'Discovery Task {i + 1}: Unknown tool {tool_name}')
            continue

        logger.info(
            f'Discovery Task {i + 1}: Calling {tool_name} for {args["db_id"] or "root"}/{args["table_name"] or "none"}',
        )

        try:
            res = DISCOVERY_TOOLS[tool_name](args)
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
