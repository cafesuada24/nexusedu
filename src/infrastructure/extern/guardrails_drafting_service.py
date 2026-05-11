import asyncio
from collections.abc import Mapping
from typing import Annotated

from guardrails import AsyncGuard, OnFailAction
from guardrails.errors import ValidationError
from guardrails.validators import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)
from pydantic import BaseModel, ConfigDict, Field

from src.application.interfaces.pii_masker import PiiMasker
from src.core.logger import logger
from src.domain.exceptions import (
    DraftGenerationError,
    TonePolicyViolationError,
    ToxicityDetectedError,
)
from src.domain.services.email_drafting import EmailDraftingService
from src.infrastructure.extern.baml_client.async_client import b as b_async
from src.infrastructure.extern.baml_client.types import EmailDraft, ToneEvaluation


@register_validator(name='ferpa_tone_validator', data_type='string')
class FerpaToneValidator(Validator):
    """Custom Guardrails validator using BAML LLM-as-a-judge for semantic tone check."""

    def _validate(
        self,
        value: str,
        metadata: Mapping[str, object],
    ) -> ValidationResult:
        """Asynchronously validate the tone using BAML."""
        subject = metadata.get('subject', 'No Subject')
        body = value

        evaluation = asyncio.run(b_async.EvaluateDraftTone(subject, body))

        match evaluation:
            case ToneEvaluation.SAFE:
                return PassResult()
            case ToneEvaluation.TOXIC:
                return FailResult(errorMessage='Toxic content detected.')
            case _:
                return FailResult(
                    errorMessage='Academic shaming or punitive tone detected.',
                )


class EmailDraftSchema(BaseModel):
    """Schema for structured email generation with attached validators."""

    model_config = ConfigDict(frozen=True)

    subject: str = Field(description='The subject line of the email.')

    body: Annotated[
        str,
        FerpaToneValidator(on_fail=OnFailAction.EXCEPTION),
    ] = Field(description='The empathetic email body content.')


class GuardrailsEmailDraftingService:
    """Robust Email Drafting Service using Guardrails AI and BAML."""

    def __init__(self, pii_masker: PiiMasker) -> None:
        self._pii_masker = pii_masker
        self._guard = AsyncGuard.for_pydantic(output_class=EmailDraftSchema)
        # self._guard = Guard.from_pydantic(EmailDraftSchema)

    async def generate_draft(
        self,
        student_name: str,
        performance_context: str,
        booking_link: str,
    ) -> tuple[str, str]:

        # 1. Mask PII in input
        masked_context = self._pii_masker.mask(performance_context)
        self._validate_input_masking(performance_context, masked_context)

        user_intent = (
            'Generate a short, supportive email to a student whose grades '
            'have dropped. Use a curious and empathetic tone.'
        )

        try:
            # 2. Structural Generation (via BAML)
            baml_output = await b_async.GenerateDraftEmail(user_intent, masked_context)

            # 3. Semantic Validation (via Guardrails AI)
            await self._validate_semantic_policy(baml_output)

            # 4. Interpolation & Invariant Verification
            subject = self._interpolate(baml_output.subject, student_name, booking_link)
            body = self._interpolate(baml_output.body, student_name, booking_link)

            self._verify_output_invariants(subject, body)

            return subject, body

        except (ToxicityDetectedError, TonePolicyViolationError):
            raise
        except Exception as e:
            raise DraftGenerationError(f'Failed to generate valid draft: {e}') from e

    async def _validate_semantic_policy(self, baml_output: EmailDraft) -> None:
        """Run semantic policy checks on the LLM output."""
        try:
            await self._guard.parse(
                llm_output=baml_output.body,
                metadata={'subject': baml_output.subject},
            )
        # Catch the specific Guardrails ValidationError
        except ValidationError as e:
            error_msg = str(e).lower()
            if 'toxic' in error_msg:
                raise ToxicityDetectedError('LLM generated toxic content.') from e
            if 'shaming' in error_msg or 'punitive' in error_msg:
                raise TonePolicyViolationError('LLM generated punitive content.') from e
            raise DraftGenerationError(
                f'Semantic guardrail validation failed: {e}'
            ) from e

    def _validate_input_masking(self, raw: str, masked: str) -> None:
        if not masked.strip() and raw.strip():
            raise DraftGenerationError('PII Masking returned empty context.')

    def _interpolate(self, text: str, name: str, link: str) -> str:
        return text.replace('{{STUDENT_NAME}}', name).replace('{{ADVISOR_LINK}}', link)

    def _verify_output_invariants(self, subject: str, body: str) -> None:
        if '{{' in subject or '{{' in body:
            raise DraftGenerationError('Draft contains un-interpolated placeholders.')
        if not subject.strip() or not body.strip():
            raise DraftGenerationError('Generated email subject or body is empty.')
