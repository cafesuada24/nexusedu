import pytest
from src.application.services.pii_masker import mask_pii

def test_mask_pii_emails():
    text = "Contact me at student@example.com or test.user+alias@sub.domain.edu"
    expected = "Contact me at [REDACTED EMAIL] or [REDACTED EMAIL]"
    assert mask_pii(text) == expected

def test_mask_pii_phone_numbers():
    # US Phone number formats
    numbers = [
        "123-456-7890",
        "(123) 456-7890",
        "123.456.7890",
        "+1 123 456 7890",
        "1234567890"
    ]
    for num in numbers:
        text = f"Call me at {num}"
        assert mask_pii(text) == "Call me at [REDACTED PHONE]"

def test_mask_pii_mixed():
    text = "Student student@school.edu (ID: 12345) can be reached at 555-0199."
    expected = "Student [REDACTED EMAIL] (ID: 12345) can be reached at [REDACTED PHONE]."
    assert mask_pii(text) == expected

def test_mask_pii_no_pii():
    text = "This is a safe string with no PII."
    assert mask_pii(text) == text

def test_mask_pii_empty():
    assert mask_pii("") == ""
    assert mask_pii(None) is None
