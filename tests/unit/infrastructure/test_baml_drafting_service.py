import pytest
from unittest.mock import AsyncMock, MagicMock
from src.infrastructure.extern.baml_drafting_service import BamlEmailDraftingService, SAFE_SUBJECT, SAFE_BODY

@pytest.fixture
def mock_baml_client(monkeypatch):
    mock_b = MagicMock()
    monkeypatch.setattr('src.infrastructure.extern.baml_drafting_service.b_async', mock_b)
    return mock_b

@pytest.mark.asyncio
async def test_generate_draft_safe(mock_baml_client):
    # Setup mock return value
    mock_draft = MagicMock()
    mock_draft.subject = "Supportive check-in"
    mock_draft.body = "Hi {{STUDENT_NAME}}, I noticed a change in your grades. Let's talk {{ADVISOR_LINK}}"
    mock_baml_client.GenerateDraftEmail = AsyncMock(return_value=mock_draft)
    
    service = BamlEmailDraftingService()
    subject, body = await service.generate_draft(
        "John", "Trend: Score 80 | Score 60", "https://link"
    )
    
    assert "John" in body
    assert "https://link" in body
    assert "Supportive check-in" in subject
    assert "noticed a change" in body

@pytest.mark.asyncio
async def test_generate_draft_tone_enforcer_subject(mock_baml_client):
    # Trigger in subject
    mock_draft = MagicMock()
    mock_draft.subject = "You are FAILING"
    mock_draft.body = "Hi {{STUDENT_NAME}}, you are doing great."
    mock_baml_client.GenerateDraftEmail = AsyncMock(return_value=mock_draft)
    
    service = BamlEmailDraftingService()
    subject, body = await service.generate_draft("John", "context", "https://link")
    
    assert subject == "Checking in on your academic progress"
    assert "support you" in body

@pytest.mark.asyncio
async def test_generate_draft_tone_enforcer_body(mock_baml_client):
    # Trigger in body
    mock_draft = MagicMock()
    mock_draft.subject = "Checking in"
    mock_draft.body = "Hi {{STUDENT_NAME}}, you are on probation."
    mock_baml_client.GenerateDraftEmail = AsyncMock(return_value=mock_draft)
    
    service = BamlEmailDraftingService()
    subject, body = await service.generate_draft("John", "context", "https://link")
    
    assert subject == "Checking in on your academic progress"
    assert "support you" in body

@pytest.mark.asyncio
async def test_generate_draft_pii_masking(mock_baml_client):
    mock_draft = MagicMock()
    mock_draft.subject = "Subject"
    mock_draft.body = "Body"
    mock_baml_client.GenerateDraftEmail = AsyncMock(return_value=mock_draft)
    
    service = BamlEmailDraftingService()
    await service.generate_draft(
        "John", "Contact student@example.com", "https://link"
    )
    
    # Verify that the context sent to BAML was masked
    call_args = mock_baml_client.GenerateDraftEmail.call_args
    assert "[REDACTED EMAIL]" in call_args.args[1]

@pytest.mark.asyncio
async def test_generate_draft_error_fallback(mock_baml_client):
    # Simulate LLM error
    mock_baml_client.GenerateDraftEmail = AsyncMock(side_effect=Exception("LLM Down"))
    
    service = BamlEmailDraftingService()
    subject, body = await service.generate_draft("John", "context", "https://link")
    
    assert subject == "Checking in on your academic progress"
    assert "John" in body
