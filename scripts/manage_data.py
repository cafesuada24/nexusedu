"""CLI script to manage data: clear analytical databases and import advisor data."""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.database.engines.duckdb_engine import DuckDBEngine
from src.database.config import DATA_DIR


def clear_databases():
    """Delete analytical duckdb files."""
    data_path = Path(DATA_DIR)
    db_files = ["lms_db.duckdb", "sis_db.duckdb"]
    
    for db_file in db_files:
        file_path = data_path / db_file
        wal_path = data_path / f"{db_file}.wal"
        
        if file_path.exists():
            os.remove(file_path)
            print(f"Deleted {file_path}")
        
        if wal_path.exists():
            os.remove(wal_path)
            print(f"Deleted {wal_path}")


def import_advisors(engine: DuckDBEngine):
    """Import advisor data from CSV into sis_db."""
    csv_path = Path("data/v2_advisors.csv")
    if not csv_path.exists():
        print(f"Error: {csv_path} not found.")
        return

    print(f"Reading {csv_path}...")
    df = pd.read_csv(csv_path)
    
    records = df.to_dict(orient="records")
    print(f"Importing {len(records)} advisors into sis_db...")
    
    # Use direct SQL via execute to ensure we can insert into the pre-defined table
    # DuckDBEngine.ingest_custom_data might create it with different types if not careful.
    # We use engine.execute with sis_db.
    
    for record in records:
        sql = "INSERT OR REPLACE INTO advisors (advisor_id, name, email) VALUES (?, ?, ?)"
        params = (record["advisor_id"], record["name"], record["email"])
        engine.execute("sis_db", sql, params=params, read_only=False)
    
    print("Advisor import completed.")


def main():
    parser = argparse.ArgumentParser(description="Manage analytical data.")
    parser.add_argument("--clear", action="store_true", help="Clear analytical databases (lms_db, sis_db)")
    parser.add_argument("--import-advisors", action="store_true", help="Import advisors from data/v2_advisors.csv")

    args = parser.parse_args()

    if args.clear:
        clear_databases()

    # Initialize engine to ensure tables are created
    engine = DuckDBEngine()
    engine.initialize_schema()

    if args.import_advisors:
        import_advisors(engine)
    
    engine.close()


if __name__ == "__main__":
    main()
