"""Unit tests for UserSettings domain entity."""

import pytest
import uuid
from src.domain.entities.settings import UserSettings

def test_create_default_user_settings():
    user_id = uuid.uuid4()
    settings = UserSettings.create_default(user_id)
    
    assert settings.user_id == user_id
    assert settings.auto_draft_enabled is True
    assert settings.ai_tone == 'warm'
    assert settings.signature is None
    assert len(settings.safety_rules) > 0

def test_update_ai_tone_valid():
    user_id = uuid.uuid4()
    settings = UserSettings.create_default(user_id)
    
    settings.update_ai_tone('formal')
    assert settings.ai_tone == 'formal'

def test_update_ai_tone_invalid():
    user_id = uuid.uuid4()
    settings = UserSettings.create_default(user_id)
    
    with pytest.raises(ValueError, match="Invalid AI tone"):
        settings.update_ai_tone('angry')

def test_update_signature_too_long():
    user_id = uuid.uuid4()
    settings = UserSettings.create_default(user_id)
    
    long_signature = "a" * 1001
    with pytest.raises(ValueError, match="Signature is too long"):
        settings.update_signature(long_signature)

def test_update_safety_rules_invalid_type():
    user_id = uuid.uuid4()
    settings = UserSettings.create_default(user_id)
    
    with pytest.raises(ValueError, match="Safety rules must be a list"):
        settings.update_safety_rules("not a list")
