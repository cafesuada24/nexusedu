import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agents.schemas import RouterPlan
from src.telemetry.logger import logger

load_dotenv()

planner_model = os.getenv('PLANNER_MODEL', 'gemini-3.1-flash-lite-preview')
logger.info(f'Initializing Planner LLM: {planner_model}')
planner_llm = ChatGoogleGenerativeAI(
    model=planner_model,
    max_retries=6,
).with_structured_output(RouterPlan).with_retry(
    wait_exponential_jitter=True,
    stop_after_attempt=6,
)
sql_gen_model = os.getenv(
    'SQL_GENERATOR_MODEL',
    os.getenv('PLANNER_MODEL', 'gemini-1.5-flash-latest'),
)
logger.info(f'Initializing SQL Generator LLM: {sql_gen_model}')
sql_gen_llm = ChatGoogleGenerativeAI(
    model=sql_gen_model,
    max_retries=6,
).with_retry(
    wait_exponential_jitter=True,
    stop_after_attempt=6,
)

determiner_model = os.getenv(
    'DETERMINER_MODEL', os.getenv('PLANNER_MODEL', 'gemini-1.5-flash-latest')
)
logger.info(f'Initializing Determiner LLM: {determiner_model}')
determiner_llm = ChatGoogleGenerativeAI(
    model=determiner_model,
    max_retries=6,
).with_retry(
    wait_exponential_jitter=True,
    stop_after_attempt=6,
)

# email_tools = EMAIL_TOOLS
# export_tools = [export_data]
#
# email_llm = ChatGoogleGenerativeAI(
#     model=os.getenv(
#         'EMAIL_AGENT_MODEL', os.getenv('PLANNER_MODEL', 'gemini-1.5-flash-latest')
#     ),
# ).bind_tools(email_tools)
#
# export_llm = ChatGoogleGenerativeAI(
#     model=os.getenv(
#         'EXPORT_AGENT_MODEL', os.getenv('PLANNER_MODEL', 'gemini-1.5-flash-latest')
#     ),
# ).bind_tools(export_tools)
