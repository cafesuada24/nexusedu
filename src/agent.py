import json
import uuid

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

# from src.agents.llms import email_tools, export_tools,
from src.agents.nodes import (
    determiner,
    discovery_node,
    email_agent_node,
    planner,
    responder_node,
    route_determiner,
    route_planner,
    sql_worker,
    visualization_agent,
)
from src.agents.state import AgentState
from src.agents.utils import extract_json_from_markdown
from src.telemetry.logger import logger

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node('planner', planner)
workflow.add_node('discovery', discovery_node)
workflow.add_node('responder', responder_node)
workflow.add_node('sql_worker', sql_worker)  # Parallel node
workflow.add_node('determiner', determiner)
workflow.add_node('viz_agent', visualization_agent)
workflow.add_node('email_agent', email_agent_node)

workflow.set_entry_point('planner')

workflow.add_conditional_edges(
    'planner',
    route_planner,
    ['discovery', 'sql_worker', 'responder'],
)

workflow.add_edge('discovery', 'planner')
workflow.add_edge('sql_worker', 'determiner')

workflow.add_conditional_edges(
    'determiner',
    route_determiner,
    {
        'visualize': 'viz_agent',
        'follow_up': 'planner',
        'finish': 'responder',
        'email_agent': 'email_agent',
    },
)

workflow.add_edge('viz_agent', 'responder')
workflow.add_edge('email_agent', 'responder')
workflow.add_edge('responder', END)

# Compile with Batching Throttle
app = workflow.compile()

if __name__ == '__main__':
    # Set session context for correlation
    session_id = str(uuid.uuid4())
    logger.set_context({'session_id': session_id})
    logger.info('Graph: Initializing execution', session_id=session_id)

    # Invoke with max_concurrency of 3
    config = {'recursion_limit': 50, 'configurable': {'max_concurrency': 3}}
    app.get_graph().print_ascii()

    user_query = "Analyze the relationship between student demographics and performance. Specifically, compare the average assessment scores from the LMS database against the different 'region' categories found in the SIS database. Provide a summary of the findings and a bar chart comparing the scores by region."

    logger.log_event('graph_start', {'user_query': user_query})

    try:
        final_result = app.invoke(
            {'messages': [HumanMessage(content=user_query)]},
            config=config,
        )
        logger.info('Graph: Execution completed successfully')
        logger.debug(f'Final Result State keys: {list(final_result.keys())}')

        viz = final_result.get('viz_json', 'NONE')
        viz = extract_json_from_markdown(viz)

        if viz:
            logger.info('Graph: Displaying visualization')
            import plotly.io as pio

            try:
                pio.from_json(json.dumps(viz)).show()
            except Exception as e:
                logger.error(f'Error displaying visualization: {e}')
        else:
            logger.info('No visualization to display.')

    except Exception as e:
        logger.error(f'Graph execution failed: {e}', exc_info=True)
    finally:
        logger.info('Graph: Finished session')
        logger.clear_context()
