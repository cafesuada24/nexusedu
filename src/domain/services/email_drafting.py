"""Port for email drafting service."""

from typing import Protocol


class EmailDraftingService(Protocol):
    """Interface for generating email drafts using AI.

    This is a Domain Port. It must not depend on Application DTOs.
    """

    async def generate_draft(
        self,
        student_name: str,
        performance_context: str,
        ai_tone: str = 'warm',
        safety_rules: list[str] | None = None,
    ) -> tuple[str, str]:
        """Generate a personalized email subject and body.

        Args:
            student_name: The name of the student.
            performance_context: A string describing recent performance trends.
            ai_tone: The desired tone for the AI (e.g., 'warm', 'formal').
            safety_rules: Additional rules the AI must follow.

        Returns:
            A tuple of (subject, body).
        """
        ...
