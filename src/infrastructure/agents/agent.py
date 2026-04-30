"""Main entry point for the Agent Assistant.

This module defines the state graph, node connections, and provides a factory
function for instantiating the compiled agent.
"""

import asyncio
import uuid
from typing import Any

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from langgraph.graph.state import Checkpointer, CompiledStateGraph

from src.domain.services.agent_metadata import AgentMetadataService
from src.infrastructure.agents.nodes import (
    discovery_node,
    email_agent_node,
    planner_node,
    responder_node,
    route_after_sql,
    route_planner,
    sql_worker_node,
)
from src.infrastructure.agents.state import AgentState
from src.infrastructure.database.session import async_session_maker
from src.infrastructure.repositories.sqlalchemy_repositories import (
    SqlAlchemyMetadataRepository,
)
from src.telemetry.logger import logger


def create_graph(
    checkpointer: Checkpointer | None = None,
) -> CompiledStateGraph[AgentState, Any, AgentState]:
    """Factory function to build and compile the agent state graph."""
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node('planner', planner_node)
    workflow.add_node('discovery', discovery_node)
    workflow.add_node('responder', responder_node)
    workflow.add_node('sql_worker', sql_worker_node)
    workflow.add_node('email_agent', email_agent_node)

    # Set Entry Point
    workflow.set_entry_point('planner')

    # Define Edges
    workflow.add_conditional_edges(
        'planner',
        route_planner,
        ['discovery', 'sql_worker', 'responder'],
    )

    workflow.add_edge('discovery', 'planner')

    workflow.add_conditional_edges(
        'sql_worker',
        route_after_sql,
        ['email_agent', 'responder'],
    )

    workflow.add_edge('email_agent', 'responder')
    workflow.add_edge('responder', END)

    return workflow.compile(checkpointer=checkpointer)


# Global app instance for API usage
app = create_graph()


async def main() -> None:
    """CLI entry point for running the graph manually."""
    load_dotenv()

    async with async_session_maker() as session:
        metadata_repo = SqlAlchemyMetadataRepository(session)
        metadata_service = AgentMetadataService(metadata_repo)

        # Set session context for correlation
        session_id = str(uuid.uuid4())
        logger.set_context({'session_id': session_id})
        logger.info('Graph: Initializing execution', session_id=session_id)

        # Configuration for execution
        config = {
            'recursion_limit': 10,
            'configurable': {
                'thread_id': session_id,
                'max_concurrency': 3,
                'metadata_service': metadata_service,
                'user_role': 'admin',
            },
        }

        # Print ASCII representation for debugging
        app.get_graph().print_ascii()

        user_query = (
            'Analyze the relationship between student demographics and performance. '
            'Specifically, compare the average assessment scores from the LMS database '
            "against the different 'region' categories found in the SIS database. "
            'Provide a summary of the findings.'
        )

        logger.log_event('graph_start', {'user_query': user_query})

        try:
            final_result = await app.ainvoke(
                {'messages': [{'role': 'user', 'content': user_query}]},
                config=config,
            )
            logger.info('Graph: Execution completed successfully')
            logger.debug(f'Final Result State keys: {list(final_result.keys())}')

        except Exception as e:
            logger.error(f'Graph execution failed: {e}', exc_info=True)
        finally:
            logger.info('Graph: Finished session')
            logger.clear_context()


if __name__ == '__main__':
    asyncio.run(main())
