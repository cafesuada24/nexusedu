"""Concurrency tests for DuckDBEngine."""

import time
from concurrent.futures import ThreadPoolExecutor

from src.database.manager import DatabaseManager


def test_duckdb_concurrency(test_db_manager: DatabaseManager) -> None:
    """Verify that multiple threads can read and write concurrently without failure."""

    def writer(thread_id: int):
        for i in range(10):
            records = [
                {
                    'sid': f'T{thread_id}_S{i}',
                    'student_name': f'Student {i}',
                    'email': f's{i}@t{thread_id}.com',
                }
            ]
            test_db_manager.ingest_records('sis_db', 'students', records)
            time.sleep(0.01)

    def reader(thread_id: int):
        for _ in range(20):
            # Concurrent read
            test_db_manager.execute(
                'sis_db', 'SELECT count(*) FROM students', read_only=True
            )
            test_db_manager.list_tables('sis_db')
            time.sleep(0.005)

    with ThreadPoolExecutor(max_workers=10) as executor:
        # Spawn multiple writers and readers
        futures = []
        for i in range(3):
            futures.append(executor.submit(writer, i))
        for i in range(7):
            futures.append(executor.submit(reader, i))

        # Wait for all to complete
        for future in futures:
            future.result()  # Will raise exception if thread failed

    # Final check
    result = test_db_manager.execute(
        'sis_db', 'SELECT count(*) as count FROM students', read_only=True
    )
    assert result[0]['count'] >= 30
