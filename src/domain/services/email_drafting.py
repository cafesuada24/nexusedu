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
        booking_link: str,
    ) -> str:
        """Generate a personalized email body.

        Args:
            student_name: The name of the student.
            performance_context: A string describing recent performance trends.
            booking_link: The URL for the student to book a meeting.

        Returns:
            The generated email body text.
        """
        ...
