import json
import re

from src.telemetry.logger import logger


class ResultSummarizer:
    @staticmethod
    def summarize(results: list[dict], max_chars: int = 4000) -> str:
        summary = []
        for res in results:
            db_id = res.get('db', 'unknown')
            data = res.get('data', [])

            # Handle error states from workers
            if isinstance(data, list) and len(data) > 0 and 'error' in data[0]:
                summary.append(f'Database: {db_id}\nError: {data[0]["error"]}\n')
                continue

            summary.append(f'Database: {db_id}')
            if isinstance(data, list):
                summary.append(f'Rows: {len(data)}')
                if len(data) > 0:
                    # Provide schema and a few sample rows
                    cols = list(data[0].keys()) if isinstance(data[0], dict) else 'N/A'
                    summary.append(f'Columns: {cols}')
                    # Use default=str to handle non-serializable objects like Timestamps
                    sample_json = json.dumps(data[:2], indent=2, default=str)
                    summary.append(f'Sample: {sample_json}')
            summary.append('-' * 20)

        return '\n'.join(summary)[:max_chars]
