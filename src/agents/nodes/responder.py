"""Node that synthesizes all available context into a final response for the user."""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.state import AgentState
from src.agents.utils import ResultSummarizer
from src.baml_client import b
from src.prompts.loader import load_prompt
from src.telemetry.logger import logger

RESPONDER_SYSTEM_PROMPT = load_prompt(
    'src/prompts/v1/responder/system.txt',
    fallback='You are a helpful data assistant. Synthesize the provided query results into a concise, professional answer for the user.',
)

def _summarize_result(state: AgentState) -> str:
    results = state.get('results', [])

    routing = state.get('routing_metadata', {})
    direct_draft = routing.get('direct_response_draft')
    discovery_context = state.get('discovery_context')

    logger.info(
        f'Responder Context: results={bool(results)}, draft={bool(direct_draft)}, discovery={bool(discovery_context)}',
    )

    context_parts: list[str] = []
    if results:
        summary = ResultSummarizer.summarize(results)
        context_parts.append(f'<sql_result>:\n\t{summary}\n</sql_result>')
        logger.debug(f'Responder Result Summary length: {len(summary)}')
    if direct_draft:
        context_parts.append(f'<planner_draft>\n\t{direct_draft}\n</planner_draft>')
    if discovery_context:
        context_parts.append(f'<discovery>\n\t{discovery_context}\n</discovery>')

    return '\n\n'.join(context_parts)



def responder_node(state: AgentState) -> dict[str, list[BaseMessage]]:
    """Node that synthesizes all available context into a final response for the user."""
    logger.info('Responder: Generating final response...')
    logger.debug(f'Responder State: {state}')


    context = _summarize_result(state)

    human_messages = [
        m for m in state.get('messages', []) if isinstance(m, HumanMessage)
    ]
    user_intent = str(human_messages[-1].content) if human_messages else 'No intent found'

    prompt = f"""
    <user_intent>
    {user_intent}
    </user_intent>

    <context>
    {context}
    </context>
    """

    logger.debug('Responder: Invoking LLM for final synthesis...')
    response = b.Respond(prompt)

    logger.info('Responder: Response generated.')
    return {'messages': [AIMessage(response)]}
