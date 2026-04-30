"""Service for providing database metadata for agent tasks."""

from typing import Any

from src.domain.repositories.interfaces import MetadataRepository
from src.infrastructure.database.config import DB_REGISTRY


class AgentMetadataService:
    """Service to bridge agent's metadata needs with repositories."""

    def __init__(self, metadata_repo: MetadataRepository) -> None:
        """Initialize with metadata repository."""
        self.metadata_repo = metadata_repo

    def get_formatted_db_list(self) -> str:
        """Retrieve list of available databases in markdown format."""
        header = '## AVAILABLE DATABASE REGISTRY\n'
        entries: list[str] = []
        for db in DB_REGISTRY:
            entry = f'### ID: `{db["id"]}`\n- **Description**: {db["description"]}\n- **Keywords**: {", ".join(db["keywords"])}\n'
            entries.append(entry)
        return header + '\n---\n'.join(entries)

    async def get_formatted_table_list(self, db_id: str) -> str:
        """List all tables available in the specified database in markdown format."""
        try:
            tables = await self.metadata_repo.list_tables(db_id)
            return f'## Tables in {db_id}:' + '\n- '.join(tables)
        except Exception as e:
            return f'Error: {e}'

    async def get_formatted_table_schema(self, db_id: str, table_name: str) -> str:
        """Get the detailed schema and sample data for a specific table in markdown format."""
        try:
            return await self.metadata_repo.get_table_schema(db_id, table_name)
        except Exception as e:
            return f'Error: {e}'

    async def execute(self, db_id: str, sql: str) -> list[dict[str, Any]]:
        """Execute a SQL query and return results."""
        return await self.metadata_repo.execute_raw(db_id, sql)
