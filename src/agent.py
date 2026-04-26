import json
import uuid

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langfuse.langchain import CallbackHandler

# from src.agents.llms import email_tools, export_tools,
from src.agents.nodes import (
    discovery_node,
    email_agent_node,
    planner,
    responder_node,
    route_after_sql,
    route_planner,
    sql_worker,
)
from src.agents.state import AgentState
from src.telemetry.logger import logger

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node('planner', planner)
workflow.add_node('discovery', discovery_node)
workflow.add_node('responder', responder_node)
workflow.add_node('sql_worker', sql_worker)  # Parallel node
workflow.add_node('email_agent', email_agent_node)

workflow.set_entry_point('planner')

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

# Compile
app = workflow.compile()

if __name__ == '__main__':
    # Set session context for correlation
    session_id = str(uuid.uuid4())
    logger.set_context({'session_id': session_id})
    logger.info('Graph: Initializing execution', session_id=session_id)

    # Initialize Langfuse Callback
    langfuse_handler = CallbackHandler()

    # Invoke with max_concurrency of 3 and Langfuse callbacks
    config = {
        'recursion_limit': 50, 
        'configurable': {'max_concurrency': 3},
        'callbacks': [langfuse_handler]
    }
    app.get_graph().print_ascii()

    user_query = "Analyze the relationship between student demographics and performance. Specifically, compare the average assessment scores from the LMS database against the different 'region' categories found in the SIS database. Provide a summary of the findings."

    logger.log_event('graph_start', {'user_query': user_query})

    try:
        final_result = app.invoke(
            {'messages': [HumanMessage(content=user_query)]},
            config=config,
        )
        logger.info('Graph: Execution completed successfully')
        logger.debug(f'Final Result State keys: {list(final_result.keys())}')

    except Exception as e:
        logger.error(f'Graph execution failed: {e}', exc_info=True)
    finally:
        logger.info('Graph: Finished session')
        logger.clear_context()
