"""Metadata repository interface."""

from typing import Any, Protocol, TypedDict


class DBDescription(TypedDict):
    """Database description for DB_REGISTRY."""

    id: str
    description: str
    dialect: str
    keywords: list[str]


class MetadataRepository(Protocol):
    """Interface for retrieving database metadata."""

    async def get_db_registry(self) -> list[DBDescription]:
        """Get the available database registry."""
        ...

    async def list_tables(self, db_id: str) -> list[str]:
        """List tables in the database."""
        ...

    async def get_table_schema(self, db_id: str, table_name: str) -> str:
        """Get schema for a table."""
        ...

    async def execute_raw(self, db_id: str, sql: str) -> list[dict[str, Any]]:
        """Execute a raw SQL query (for analysis)."""
        ...
