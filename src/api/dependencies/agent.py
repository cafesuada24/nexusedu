"""Dependencies for the Agent Assistant API.

This module provides the compiled LangGraph agent with persistent memory
as a FastAPI dependency.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from src.agent import workflow
from src.agents.state import AgentState

# Initialize MemorySaver for thread-level persistence
memory = MemorySaver()

# Compile the workflow with the checkpointer for the API
agent_with_memory = workflow.compile(checkpointer=memory)

def get_agent() -> CompiledStateGraph[AgentState, None, AgentState, AgentState]:
    """Dependency provider for the compiled LangGraph agent.

    Returns:
        The compiled LangGraph workflow with memory persistence.
    """
    return agent_with_memory
