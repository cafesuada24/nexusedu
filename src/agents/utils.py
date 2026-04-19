import json
import re
from src.telemetry.logger import logger


def extract_json_from_markdown(text: str) -> dict:
    """Extracts JSON from markdown code blocks or raw text."""
    if not text or text == 'NONE':
        return {}

    # If already a dict, return it
    if isinstance(text, dict):
        return text

    # Try to find JSON in code blocks
    pattern = r'```json\s*(.*?)\s*```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        json_string = match.group(1)
    else:
        # Fallback: find the first '{' and last '}'
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_string = text[start : end + 1]
        else:
            json_string = text

    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        logger.error(f'Invalid JSON format: {e}. Text: {text[:100]}...')
        return {}


class ResultSummarizer:
    @staticmethod
    def to_distilled_csv(results: list[dict]) -> str:
        """Converts multiple DB results into a compact CSV-like format for LLM consumption."""
        output = []
        for res in results:
            db_id = res.get('db', 'unknown')
            data = res.get('data', [])

            if not isinstance(data, list) or len(data) == 0:
                continue

            output.append(f'### Data from: {db_id}')
            # Filter out internal keys like '_truncated'
            clean_data = [
                {k: v for k, v in row.items() if not k.startswith('_')}
                for row in data
                if isinstance(row, dict)
            ]

            if clean_data:
                import pandas as pd

                df = pd.DataFrame(clean_data)
                output.append(df.to_csv(index=False))
            output.append('-' * 10)

        return '\n'.join(output)

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
                    summary.append(f'Sample: {json.dumps(data[:2], indent=2)}')
            summary.append('-' * 20)

        return '\n'.join(summary)[:max_chars]
