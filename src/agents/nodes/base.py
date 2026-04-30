"""Base protocol and common utilities for agent nodes."""

from typing import Protocol, runtime_checkable

from langchain_core.runnables import RunnableConfig

from src.agents.state import AgentState


@runtime_checkable
class AgentNode(Protocol):
    """Protocol for a node in the agent state graph."""

    def __call__(
        self, state: AgentState, config: RunnableConfig
    ) -> dict[str, object] | object:
        """Execute the node logic."""
        ...
