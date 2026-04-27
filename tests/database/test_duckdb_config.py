"""Tests for DuckDBEngine configuration (MotherDuck and Concurrency)."""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest
import duckdb

from src.database.engines.duckdb_engine import DuckDBEngine


def test_duckdb_engine_local_fallback(tmp_path) -> None:
    """Verify DuckDBEngine uses local connection when MOTHERDUCK_TOKEN is unset."""
    with patch.dict(os.environ, {}, clear=True):
        engine = DuckDBEngine(data_dir=tmp_path)
        assert engine.is_motherduck is False
        assert hasattr(engine, '_main_conn')


@patch('src.database.engines.duckdb_engine.duckdb.connect')
def test_duckdb_engine_motherduck_connection(mock_connect, tmp_path) -> None:
    """Verify DuckDBEngine connects to MotherDuck when token is present."""
    fake_token = "fake_md_token_123"
    
    with patch.dict(os.environ, {"MOTHERDUCK_TOKEN": fake_token}):
        engine = DuckDBEngine(data_dir=tmp_path)
        
        assert engine.is_motherduck is True
        mock_connect.assert_called_once_with(f'md:?motherduck_token={fake_token}')
