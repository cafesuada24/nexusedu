"""BAML implementation of the EmailDraftingService."""

from dotenv import load_dotenv

from src.domain.services.email_drafting import EmailDraftingService
from src.infrastructure.extern.baml_client.async_client import b as b_async

load_dotenv()



class BamlEmailDraftingService(EmailDraftingService):
    """Adapter for BAML-based email drafting."""

    async def generate_draft(
        self, student_name: str, performance_context: str, booking_link: str,
    ) -> str:
        """Generate a personalized email body using BAML."""
        user_intent = (
            'Generate a short, supportive email to a student whose grades have dropped. '
            'Mention their recent performance trend and offer a meeting.'
        )
        ai_response = await b_async.GenerateDraftEmail(user_intent, performance_context)

        # Interpolation
        personalized_body = ai_response.replace('{{STUDENT_NAME}}', student_name)
        return personalized_body.replace('{{ADVISOR_LINK}}', booking_link)

