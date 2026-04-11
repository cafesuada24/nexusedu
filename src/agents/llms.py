import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.agents.schemas import RouterPlan
from src.tools.db import get_db_list

# from src.tools.email import EMAIL_TOOLS
# from src.tools.export_data_tool import export_data

from src.telemetry.logger import logger

load_dotenv()

planner_model = os.getenv('PLANNER_MODEL', 'gemini-1.5-flash-latest')
logger.info(f'Initializing Planner LLM: {planner_model}')
planner_llm = ChatGoogleGenerativeAI(
    model=planner_model,
).with_structured_output(RouterPlan)

sql_gen_model = os.getenv(
    'SQL_GENERATOR_MODEL',
    os.getenv('PLANNER_MODEL', 'gemini-1.5-flash-latest'),
)
logger.info(f'Initializing SQL Generator LLM: {sql_gen_model}')
sql_gen_llm = ChatGoogleGenerativeAI(
    model=sql_gen_model,
    # base_url=os.getenv('OLLAMA_BASE_URL'),
    # api_key=os.getenv('OLLAMA_API_KEY'),
)

determiner_model = os.getenv(
    'DETERMINER_MODEL', os.getenv('PLANNER_MODEL', 'gemini-1.5-flash-latest')
)
logger.info(f'Initializing Determiner LLM: {determiner_model}')
determiner_llm = ChatGoogleGenerativeAI(
    model=determiner_model,
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
