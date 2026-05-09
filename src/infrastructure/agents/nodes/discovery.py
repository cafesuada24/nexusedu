"""Node that performs schema discovery using database tools."""

from typing import TYPE_CHECKING, Any

from langchain_core.runnables import RunnableConfig

if TYPE_CHECKING:
    from src.infrastructure.database.manager import DatabaseManager

from src.core.logger import logger
from src.infrastructure.agents.state import (
    AgentState,
    DiscoveryRequest,
    RoutingMetadata,
)

MAX_DISCOVERY_CONTEXT_CHARS = 15_000


class DiscoveryNode:
    """Performs schema discovery using database tools."""

    async def __call__(self, state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        """Execute the discovery node."""
        logger.info('Discovery: Executing tools...')

        routing: RoutingMetadata = state.get('routing_metadata', {})
        discovery_requests = routing.get('discovery_requests', [])
        new_context_parts: list[str] = []

        db_manager = config.get('configurable', {}).get('db_manager')
        if not db_manager:
            logger.error('Discovery: db_manager not found in config')
            raise ValueError('db_manager not found in config')

        logger.info(f'Discovery: Processing {len(discovery_requests)} requests')

        for i, req in enumerate(discovery_requests):
            res = await self._process_request(db_manager, req, i)
            if res:
                new_context_parts.append(res)

        current_context = state.get('discovery_context') or ''
        updated_context = f'{current_context}\n\n' + '\n\n'.join(new_context_parts)

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

    async def _process_request(
        self,
        db_manager: 'DatabaseManager[Any, Any]',
        req: DiscoveryRequest | dict[str, Any],
        index: int,
    ) -> str | None:
        """Process a single discovery request."""
        # Normalize request to model
        req_model = DiscoveryRequest(**req) if isinstance(req, dict) else req

        tool_name = req_model.tool_name
        db_id = req_model.db_id
        table_name = req_model.table_name

        logger.info(
            f'Discovery Task {index + 1}: Calling {tool_name} for {db_id or "root"}/{table_name or "none"}',
        )

        try:
            match tool_name:
                case 'get_db_list':
                    res = await db_manager.get_formatted_db_list()
                case 'list_tables' if db_id:
                    res = await db_manager.get_formatted_table_list(db_id=db_id)
                case 'describe_table' if db_id and table_name:
                    res = await db_manager.get_formatted_table_schema(
                        db_id=db_id,
                        table_name=table_name,
                    )
                case _:
                    logger.warning(
                        f'Discovery Task {index + 1}: Unknown tool {tool_name} or missing args',
                    )
                    return None

            if res:
                logger.debug(
                    f'Discovery Task {index + 1} Result length: {len(str(res))}',
                )
                return str(res)
        except Exception as e:
            logger.error(
                f'Discovery Task {index + 1} ({tool_name}) failed: {e}',
                exc_info=True,
            )

        return None


discovery_node = DiscoveryNode()
