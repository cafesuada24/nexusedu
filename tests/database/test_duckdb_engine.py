"""Tests for the DuckDBEngine implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.manager import DatabaseManager

def test_initialize_schema(test_db_manager: DatabaseManager) -> None:
    """Verify that initialize_schema creates the expected tables."""
    tables = test_db_manager.list_tables('sis_db')
    assert 'students' in tables
    assert 'student_status_history' in tables

    tables_lms = test_db_manager.list_tables('lms_db')
    assert 'activities' in tables_lms

def test_ingest_records(test_db_manager: DatabaseManager) -> None:
    """Verify that ingest_records inserts data correctly."""
    records = [
        {'sid': 'S001', 'student_name': 'Alice', 'email': 'alice@example.com'},
    ]
    test_db_manager.ingest_records('sis_db', 'students', records)

    results = test_db_manager.execute('sis_db', 'SELECT * FROM students')
    assert len(results) == 1
    assert results[0]['sid'] == 'S001'
    assert results[0]['student_name'] == 'Alice'

def test_ingest_custom_data(test_db_manager: DatabaseManager) -> None:
    """Verify that ingest_custom_data creates dynamic tables."""
    records = [{'col1': 'val1', 'col2': 2}]
    test_db_manager.ingest_custom_data('custom_table', records)

    tables = test_db_manager.list_tables('sis_db')
    assert 'custom_table' in tables

    results = test_db_manager.execute('sis_db', 'SELECT * FROM custom_table')
    assert len(results) == 1
    assert results[0]['col1'] == 'val1'

def test_execute_read_only_protection(test_db_manager: DatabaseManager) -> None:
    """Verify that execute blocks destructive commands in read_only mode."""
    # Ensure a table exists
    test_db_manager.ingest_custom_data('safe_table', [{'id': 1}])

    # Try to drop it
    result = test_db_manager.execute('sis_db', 'DROP TABLE safe_table', read_only=True)
    assert 'error' in result[0]
    assert 'Blocked' in result[0]['error']

    # Verify table still exists
    tables = test_db_manager.list_tables('sis_db')
    assert 'safe_table' in tables

def test_execute_multi_statement_blocked(test_db_manager: DatabaseManager) -> None:
    """Verify that multi-statement queries are blocked."""
    sql = "SELECT 1; SELECT 2;"
    result = test_db_manager.execute('sis_db', sql, read_only=True)
    assert 'error' in result[0]
    assert 'Multiple statements' in result[0]['error']

def test_execute_statement_type_blocked(test_db_manager: DatabaseManager) -> None:
    """Verify that disallowed statement types are blocked in read-only mode."""
    sql = "INSERT INTO students (sid, student_name) VALUES ('S999', 'Malicious')"
    result = test_db_manager.execute('sis_db', sql, read_only=True)
    assert 'error' in result[0]
    assert 'Blocked: Statement type Insert is not allowed' in result[0]['error']

def test_execute_bypass_blocked(test_db_manager: DatabaseManager) -> None:
    """Verify that multi-statement bypass attempts are blocked."""
    sql = "SELECT 1; DROP TABLE students;"
    result = test_db_manager.execute('sis_db', sql, read_only=True)
    assert 'error' in result[0]
    assert 'Multiple statements' in result[0]['error']
