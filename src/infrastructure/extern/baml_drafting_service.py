"""BAML implementation of the EmailDraftingService."""

import re
from dotenv import load_dotenv

from src.application.services.pii_masker import mask_pii
from src.domain.services.email_drafting import EmailDraftingService
from src.infrastructure.extern.baml_client.async_client import b as b_async

load_dotenv()

# Academic Shame triggers for Tone Enforcer
SHAME_TRIGGERS = [
    r'\bfail(ing|ure|ed)?\b',
    r'\bprobation\b',
    r'\bdisappoint(ing|ed)?\b',
    r'\brisk\b',
    r'\bwarning\b',
    r'\bpoor\b',
    r'\badverse\b',
]
SHAME_REGEX = re.compile('|'.join(SHAME_TRIGGERS), re.IGNORECASE)

SAFE_SUBJECT = 'Checking in on your academic progress'
SAFE_BODY = (
    'Hi {{STUDENT_NAME}},\n\n'
    'I noticed a change in your recent course activity and wanted to check in to see how things are going. '
    'We are here to support you and help you navigate any challenges you might be facing.\n\n'
    'If you have a moment, I would love to chat and see how we can help. '
    'You can book a time with me here: {{ADVISOR_LINK}}\n\n'
    'Best regards,\n'
    'Your Academic Advisor'
)


class BamlEmailDraftingService(EmailDraftingService):
    """Adapter for BAML-based email drafting with FERPA guardrails."""

    async def generate_draft(
        self, student_name: str, performance_context: str, booking_link: str,
    ) -> tuple[str, str]:
        """Generate a personalized email subject and body using BAML with PII masking and tone enforcer."""

        # 1. PII Masking (Input Guardrail)
        masked_context = mask_pii(performance_context)

        user_intent = (
            'Generate a short, supportive email to a student whose grades have dropped. '
            'Mention their recent performance trend and offer a meeting. '
            'Be curious and empathetic. Do NOT use words like "failure" or "risk".'
        )

        try:
            # 2. Structural Validation (via BAML class return type)
            email_draft = await b_async.GenerateDraftEmail(user_intent, masked_context)
            subject = email_draft.subject
            body = email_draft.body

            # 3. Tone & Policy Enforcer (Output Guardrail)
            if SHAME_REGEX.search(subject) or SHAME_REGEX.search(body):
                subject = SAFE_SUBJECT
                body = SAFE_BODY
        except Exception:
            # Fallback for any LLM or parsing errors
            subject = SAFE_SUBJECT
            body = SAFE_BODY

        # Interpolation
        final_subject = subject.replace('{{STUDENT_NAME}}', student_name)
        final_subject = final_subject.replace('{{ADVISOR_LINK}}', booking_link)

        final_body = body.replace('{{STUDENT_NAME}}', student_name)
        final_body = final_body.replace('{{ADVISOR_LINK}}', booking_link)

        return final_subject, final_body


