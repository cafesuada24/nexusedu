import structlog

from src.application.interfaces.pii_masker import PiiMasker
from src.domain.exceptions import (
    DraftGenerationError,
    TonePolicyViolationError,
    ToxicityDetectedError,
)
from src.infrastructure.extern.baml_client.async_client import b as b_async
from src.infrastructure.extern.baml_client.types import EmailDraft

logger = structlog.get_logger(__name__)


class GuardrailsEmailDraftingService:
    """Robust Email Drafting Service using BAML and local heuristics.

    Note: Guardrails AI dependency was removed due to quarantine; replaced with
    pure Python heuristics for tone validation.
    """

    def __init__(self, pii_masker: PiiMasker) -> None:
        self._pii_masker = pii_masker

    async def generate_draft(
        self,
        student_name: str,
        performance_context: str,
    ) -> tuple[str, str]:

        # 1. Mask PII in input
        logger.info('Masking PII in performance context...')
        masked_context = self._pii_masker.mask(performance_context)
        self._validate_input_masking(performance_context, masked_context)

        user_intent = (
            'Generate a short, supportive email to a student whose grades '
            'have dropped. Use a curious and empathetic tone.'
        )

        try:
            # 2. Structural Generation (via BAML)
            baml_output = await b_async.GenerateDraftEmail(user_intent, masked_context)

            # 3. Semantic Validation (via local heuristics)
            self._validate_semantic_policy(baml_output)

            # 4. Interpolation & Invariant Verification
            subject = self._interpolate(baml_output.subject, student_name)
            body = self._interpolate(baml_output.body, student_name)

            self._verify_output_invariants(subject, body)

            return subject, body

        except (ToxicityDetectedError, TonePolicyViolationError):
            raise
        except (Exception, TimeoutError) as e:
            logger.error('Draft generation error', error=str(e), exc_info=True)
            raise DraftGenerationError(f'Failed to generate valid draft: {e}') from e

    def _validate_semantic_policy(self, baml_output: EmailDraft) -> None:
        """Run semantic policy checks on the LLM output using local heuristics."""
        logger.info('Validating body tone', subject=baml_output.subject)

        body_lower = baml_output.body.lower()
        punitive_words = [
            'failure',
            'probation',
            'risk',
            'failed',
            'disappointing',
            'warning',
            'punishment',
            'consequence',
            'shaming',
        ]

        for word in punitive_words:
            if word in body_lower:
                logger.info(
                    'Tone evaluation failed',
                    punitive_word=word,
                )
                raise TonePolicyViolationError(
                    f'Academic shaming or punitive tone detected: "{word}"',
                )

        logger.info('Tone evaluation passed (SAFE).')

    def _validate_input_masking(self, raw: str, masked: str) -> None:
        if not masked.strip() and raw.strip():
            raise DraftGenerationError('PII Masking returned empty context.')

    def _interpolate(self, text: str, name: str) -> str:
        return text.replace('{{STUDENT_NAME}}', name)

    def _verify_output_invariants(self, subject: str, body: str) -> None:
        if '{{' in subject or '{{' in body:
            raise DraftGenerationError('Draft contains un-interpolated placeholders.')
        if not subject.strip() or not body.strip():
            raise DraftGenerationError('Generated email subject or body is empty.')
