import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import Send

from src.agents.llms import (
    planner_llm,
    sql_gen_llm,
)
from src.agents.schemas import (
    DiscoveryRequest,
    PlannerOutput,
    RouterPlan,
    SQLGeneration,
)
from src.agents.state import AgentState, SQLTask
from src.agents.utils import ResultSummarizer
from src.telemetry.logger import logger
from src.tools.db import (
    describe_table,
    execute_sql,
    get_db_list,
    get_db_schema,
    list_tables,
)


# Prompt loading logic
def load_prompt(path: str, fallback: str = '') -> str:
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f'Prompt file not found: {path}')
        return fallback


# Use the paths found in the repository
PLANNER_SYSTEM_PROMPT = load_prompt('src/prompts/v1/planner/system.txt')
RESPONDER_SYSTEM_PROMPT = load_prompt(
    'src/prompts/v1/responder/system.txt',
    fallback='You are a helpful data assistant. Synthesize the provided query results into a concise, professional answer for the user.',
)
# Missing in repo, using placeholder or empty string
SQL_GENERATOR_SYSTEM_PROMPT = load_prompt(
    'src/prompts/v1/sql_generator/system.txt',
    fallback='You are a SQL expert. Generate SQL for the given task.',
)
EMAIL_GENERATOR_SYSTEM_PROMPT = load_prompt(
    'src/prompts/v1/email_generator/system.txt',
    fallback='You are an email specialist. Draft an empathetic nudge email for the student.',
)


def planner(state: AgentState) -> dict:
    logger.info('Planner: Executing...')
    logger.debug(f'Planner Input State: {state}')

    # Include discovery context in the prompt if available
    discovery_info = ''
    if state.get('discovery_context'):
        logger.info('Planner: Incorporating discovery context.')
        discovery_info = f'\n\n<discovery_context>\n{state["discovery_context"]}\n</discovery_context>'
        logger.debug(f'Discovery Context Length: {len(state["discovery_context"])}')

    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT + discovery_info)
    ] + state.get('messages', [])

    # 2. Invoke the model (it returns a RouterPlan because of with_structured_output in llms.py)
    logger.debug('Planner: Invoking LLM...')
    plan: RouterPlan = planner_llm.invoke(messages)

    logger.info(f'Planner Path Decision: {plan.path}')
    logger.log_event(
        'planner_output',
        {
            'path': plan.path,
            'tasks_count': len(plan.tasks) if plan.tasks else 0,
            'discovery_requests_count': len(plan.discovery_requests)
            if plan.discovery_requests
            else 0,
            'has_direct_response': bool(plan.direct_response_draft),
        },
    )

    update = {
        'routing_metadata': {
            'path': plan.path,
            'direct_response_draft': plan.direct_response_draft,
            'discovery_requests': plan.discovery_requests or [],
            'next_action_after_sql': plan.next_action_after_sql or 'RESPOND',
        },
    }

    # Reset results and data if this is a fresh query (not a follow-up loop)
    if state.get('next_step') != 'follow_up':
        logger.info('Planner: Fresh query detected, resetting results.')
        update['results'] = None
    else:
        logger.info('Planner: Follow-up iteration, preserving existing results.')

    if plan.path == 'SQL_EXECUTION' and plan.tasks:
        logger.debug(f'Planner Tasks: {plan.tasks}')
        update['tasks'] = [task.model_dump() for task in plan.tasks]
    else:
        update['tasks'] = []

    return update


def discovery_node(state: AgentState) -> dict:
    logger.info('Discovery: Executing tools...')
    routing = state.get('routing_metadata', {})
    discovery_requests = routing.get('discovery_requests') or []
    new_context_parts = []

    logger.info(f'Discovery: Processing {len(discovery_requests)} requests')

    for i, req in enumerate(discovery_requests):
        # Check if it's a DiscoveryRequest object or a dict
        tool_name = req.tool_name if hasattr(req, 'tool_name') else req.get('tool_name')
        db_id = req.db_id if hasattr(req, 'db_id') else req.get('db_id')
        table_name = (
            req.table_name if hasattr(req, 'table_name') else req.get('table_name')
        )

        logger.info(
            f'Discovery Task {i + 1}: Calling {tool_name} for {db_id or "root"}/{table_name or "none"}'
        )

        try:
            if tool_name == 'get_db_list':
                res = get_db_list.invoke({})
                new_context_parts.append(res)
            elif tool_name == 'list_tables':
                if db_id:
                    res = list_tables.invoke({'db_id': db_id})
                    new_context_parts.append(res)
            elif tool_name == 'describe_table':
                if db_id and table_name:
                    res = describe_table.invoke(
                        {'db_id': db_id, 'table_name': table_name}
                    )
                    new_context_parts.append(res)

            logger.debug(
                f'Discovery Task {i + 1} Result: {new_context_parts[-1] if new_context_parts else "No result"}'
            )
        except Exception as e:
            logger.error(
                f'Discovery Task {i + 1} ({tool_name}) failed: {e}', exc_info=True
            )

    current_context = state.get('discovery_context') or ''
    updated_context = current_context + '\n\n' + '\n\n'.join(new_context_parts)

    logger.info(f'Discovery: Updated context length: {len(updated_context)}')

    return {
        'discovery_context': updated_context,
        'routing_metadata': {
            **routing,
            'discovery_requests': [],
        },  # Clear processed requests but keep path
    }


def responder_node(state: AgentState) -> dict:
    logger.info('Responder: Generating final response...')
    logger.debug(f'Responder State: {state}')

    # Use results if available, or direct_response_draft
    results = state.get('results', [])
    routing = state.get('routing_metadata', {})
    direct_draft = routing.get('direct_response_draft')
    discovery_context = state.get('discovery_context')

    logger.info(
        f'Responder Context: results={bool(results)}, draft={bool(direct_draft)}, discovery={bool(discovery_context)}'
    )

    context_parts = []
    if results:
        summary = ResultSummarizer.summarize(results)
        context_parts.append(f'SQL Results:\n{summary}')
        logger.debug(f'Responder Result Summary: {summary[:200]}...')
    if direct_draft:
        context_parts.append(f'Planner Draft:\n{direct_draft}')
    if discovery_context:
        context_parts.append(f'Discovery Information:\n{discovery_context}')

    context = '\n\n'.join(context_parts)

    # Use the last human message or first one as user intent
    human_messages = [
        m for m in state.get('messages', []) if isinstance(m, HumanMessage)
    ]
    user_intent = human_messages[-1].content if human_messages else 'No intent found'

    messages = [
        SystemMessage(content=RESPONDER_SYSTEM_PROMPT),
        HumanMessage(
            content=f'User Intent: {user_intent}\n\nContext:\n{context}',
        ),
    ]

    logger.debug('Responder: Invoking LLM for final synthesis...')
    response = sql_gen_llm.invoke(messages)  # Use any LLM for final response

    logger.info('Responder: Response generated.')
    logger.debug(f'Final Response: {response.content[:500]}...')

    return {'messages': [response]}


def sql_worker(state: SQLTask) -> dict:
    db_id = state['db_id']
    logger.info(f'SQL_Worker [{db_id}]: Starting task...')
    logger.debug(f'SQL_Worker [{db_id}] Intent: {state["query_intent"]}')

    prompt = [SystemMessage(content=SQL_GENERATOR_SYSTEM_PROMPT), state['message']]

    # Use structured output for SQL generation
    sql_gen_with_output = sql_gen_llm.with_structured_output(SQLGeneration)
    sql_query = None
    try:
        logger.debug(f'SQL_Worker [{db_id}]: Generating SQL...')
        sql_data = sql_gen_with_output.invoke(prompt)
        sql_query = sql_data.sql
    except Exception as e:
        logger.warning(f'SQL_Worker [{db_id}] failed structured output: {e}')
        # Fallback to standard invoke if needed
        response = sql_gen_llm.invoke(prompt)
        content = response.content

        # Try to extract SQL from markdown if present
        sql_match = re.search(
            r'```sql\s*(.*?)\s*```', content, re.DOTALL | re.IGNORECASE
        )
        if sql_match:
            sql_query = sql_match.group(1).strip()
        else:
            # If no markdown, just take the whole content and hope it's raw SQL
            sql_query = content.strip()

    if not sql_query:
        logger.error(f'SQL_Worker [{db_id}]: Failed to generate SQL query.')
        return {
            'results': [{'db': db_id, 'data': [{'error': 'Failed to generate SQL'}]}]
        }

    logger.info(f'SQL_Worker [{db_id}]: Generated SQL: {sql_query}')
    logger.log_event('sql_generated', {'db_id': db_id, 'sql': sql_query})

    try:
        logger.info(f'SQL_Worker [{db_id}]: Executing query...')
        raw_data = execute_sql(db_id, sql_query)
        logger.info(
            f'SQL_Worker [{db_id}]: Execution successful. Rows: {len(raw_data)}'
        )
        logger.log_event(
            'sql_execution_success', {'db_id': db_id, 'rows': len(raw_data)}
        )
    except Exception as e:
        logger.error(f'Execution error on {db_id}: {e}', exc_info=True)
        raw_data = [{'error': str(e)}]
        logger.log_event('sql_execution_error', {'db_id': db_id, 'error': str(e)})

    return {
        'results': [{'db': db_id, 'data': raw_data}],
    }


def email_agent_node(state: AgentState) -> dict:
    """Dedicated node for generating personalized email drafts."""
    logger.info('Email Agent: Generating draft...')

    results = state.get('results', [])
    summary = ResultSummarizer.summarize(results)

    human_messages = [
        m for m in state.get('messages', []) if isinstance(m, HumanMessage)
    ]
    user_intent = (
        human_messages[-1].content if human_messages else 'Generate nudge email'
    )

    messages = [
        SystemMessage(content=EMAIL_GENERATOR_SYSTEM_PROMPT),
        HumanMessage(
            content=f'User Intent: {user_intent}\n\nContext:\n{summary}',
        ),
    ]

    logger.debug('Email Agent: Invoking LLM for email drafting...')
    response = sql_gen_llm.invoke(messages)

    logger.info('Email Agent: Draft generated.')
    return {'messages': [response]}


def route_after_sql(state: AgentState):
    routing = state.get('routing_metadata', {})
    next_action = routing.get('next_action_after_sql', 'RESPOND')
    
    logger.info(f'Routing (After SQL): Choosing path "{next_action}"')
    
    if next_action == 'EMAIL_DRAFT':
        return 'email_agent'
        
    return 'responder'


def route_planner(state: AgentState):
    routing = state.get('routing_metadata', {})
    path = routing.get('path')

    logger.info(f'Routing (Planner): Choosing path "{path}"')

    if path == 'DISCOVERY_REQUIRED':
        return 'discovery'
    if path == 'DIRECT_ANSWER':
        return 'responder'

    if not state.get('tasks'):
        logger.warning(
            'Routing (Planner): Path was SQL_EXECUTION but no tasks found. Routing to responder.'
        )
        return 'responder'

    logger.info(
        f'Routing (Planner): Sending tasks to {len(state["tasks"])} SQL workers.'
    )

    sends = [
        Send(
            'sql_worker',
            {
                'db_id': task['db_id'],
                'dialect': task['dialect'],
                'query_intent': task['query_intent'],
                'schema_hint': task.get('schema_hint', ''),
                'message': HumanMessage(
                    content=(
                        f'Generate SQL for {task["db_id"]}.\n'
                        f'**SQL Dialect:** {task["dialect"]}.\n'
                        f'**Intent:** {task["query_intent"]}.\n'
                        f'**Hints:** {task.get("schema_hint", "")}\n'
                        f'**Database schema:**\n{get_db_schema(task["db_id"])}'
                    ),
                ),
            },
        )
        for task in state['tasks']
    ]

    logger.debug(f'Routing (Planner): Send operations: {sends}')
    return sends
