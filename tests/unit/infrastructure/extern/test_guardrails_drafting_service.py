import pytest
from unittest.mock import AsyncMock, MagicMock
from src.infrastructure.extern.guardrails_drafting_service import GuardrailsEmailDraftingService
from src.domain.exceptions import TonePolicyViolationError, DraftGenerationError
from src.infrastructure.extern.baml_client.types import EmailDraft

@pytest.fixture
def mock_pii_masker():
    masker = MagicMock()
    masker.mask.side_effect = lambda x: x
    return masker

@pytest.fixture
def service(mock_pii_masker):
    return GuardrailsEmailDraftingService(pii_masker=mock_pii_masker)

@pytest.mark.asyncio
async def test_generate_draft_success(service, monkeypatch):
    mock_b = AsyncMock()
    mock_b.GenerateDraftEmail.return_value = EmailDraft(
        subject="Support for your progress",
        body="Dear {{STUDENT_NAME}}, we are here to help. Book here: {{ADVISOR_LINK}}"
    )
    monkeypatch.setattr('src.infrastructure.extern.guardrails_drafting_service.b_async', mock_b)

    subject, body = await service.generate_draft(
        student_name="John",
        performance_context="Grades are slipping.",
        booking_link="http://book.me"
    )

    assert "John" in subject or "John" in body
    assert "John" in body
    assert "http://book.me" in body
    assert "failure" not in body.lower()

@pytest.mark.asyncio
async def test_generate_draft_tone_violation(service, monkeypatch):
    mock_b = AsyncMock()
    mock_b.GenerateDraftEmail.return_value = EmailDraft(
        subject="Your failure",
        body="You have failed significantly. This is a warning."
    )
    monkeypatch.setattr('src.infrastructure.extern.guardrails_drafting_service.b_async', mock_b)

    with pytest.raises(TonePolicyViolationError) as exc:
        await service.generate_draft(
            student_name="John",
            performance_context="Grades are slipping.",
            booking_link="http://book.me"
        )
    assert "punitive tone detected" in str(exc.value)

@pytest.mark.asyncio
async def test_generate_draft_empty_masking_error(service, mock_pii_masker, monkeypatch):
    mock_pii_masker.mask.side_effect = None
    mock_pii_masker.mask.return_value = ""
    mock_b = AsyncMock()
    mock_b.GenerateDraftEmail.return_value = EmailDraft(
        subject="S", body="B"
    )
    monkeypatch.setattr('src.infrastructure.extern.guardrails_drafting_service.b_async', mock_b)
    
    with pytest.raises(DraftGenerationError) as exc:
        await service.generate_draft(
            student_name="John",
            performance_context="Some context",
            booking_link="http://book.me"
        )
    assert "PII Masking returned empty context" in str(exc.value)
