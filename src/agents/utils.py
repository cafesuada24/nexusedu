import json
import re

import yaml

from src.agents.state import ResultList
# from src.models import Event, Thread
# from src.telemetry.logger import logger


def stringifyToYaml(obj: object) -> str:
    data = obj if isinstance(obj, dict) else vars(obj)
    dumped_yaml = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
    )
    return '\n'.join('  ' + line for line in dumped_yaml.splitlines())

#
# def event_to_prompt(event: Event) -> str:
#     """Convert an event to XML tag format."""
#     data = event.data if isinstance(event.data, str) else stringifyToYaml(event.data)
#     return f'<{event.type.value}>\n{data}\n</{event.type.value}>'
#
#
# def thread_to_prompt(thread: Thread) -> str:
#     """Convert a thread to XML tag format."""
#     return '\n\n'.join(event_to_prompt(event) for event in thread.events)


class ResultSummarizer:

    @staticmethod
    def summarize(results: ResultList, max_chars: int = 4000) -> str:
        summary: list[str] = []
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


# if __name__ == '__main__':
#     import uuid
#     from models import EmailMessage, EventType
#
#     thread = Thread(ticket_id=uuid.uuid4())
#     thread.events = [
#         Event(
#             thread_id=thread.id,
#             type=EventType.EMAIL_MESSAGE,
#             data=EmailMessage(
#                 user_email='123',
#                 content="""
#             lskjfklasjfkdjfkajfkafk
#             aksfjlksjflkds
#
#
#             asfkksadlk;fjksldfjas
#             kasfjsljkdl
#             """,
#             ),
#         )
#     ]
#
#     print(thread_to_prompt(thread))
