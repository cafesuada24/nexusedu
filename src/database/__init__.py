"""Database package for multi-source DB access and anomaly detection."""

from src.database.config import DB_REGISTRY
from src.database.manager import DatabaseManager

__all__ = ['DatabaseManager', 'DB_REGISTRY']
