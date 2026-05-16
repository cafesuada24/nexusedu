"""User settings domain entity."""

from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.base import AggregateRoot


@dataclass
class UserSettings(AggregateRoot):
    """Domain model for user-specific settings."""

    user_id: UUID
    auto_draft_enabled: bool
    ai_tone: str
    signature: str | None
    safety_rules: list[str]

    def update_auto_draft(self, enabled: bool) -> None:
        """Update the auto-drafting setting."""
        self.auto_draft_enabled = enabled

    def update_ai_tone(self, tone: str) -> None:
        """Update the AI tone setting with invariant check."""
        allowed_tones = {'warm', 'formal', 'direct', 'motivational'}
        if tone not in allowed_tones:
            raise ValueError(f"Invalid AI tone: {tone}. Must be one of {allowed_tones}")
        self.ai_tone = tone

    def update_signature(self, signature: str | None) -> None:
        """Update the signature."""
        if signature and len(signature) > 1000:
            raise ValueError("Signature is too long (max 1000 characters)")
        self.signature = signature

    def update_safety_rules(self, rules: list[str]) -> None:
        """Update safety rules."""
        if not isinstance(rules, list):
            raise ValueError("Safety rules must be a list of strings")
        self.safety_rules = rules

    @classmethod
    def create_default(cls, user_id: UUID, name: str | None = None) -> 'UserSettings':
        """Create default settings for a new user."""
        signature_name = name if name else 'Academic Advisor'
        return cls(
            user_id=user_id,
            auto_draft_enabled=True,
            ai_tone='warm',
            signature=f'Best regards,\n{signature_name}\nAcademic Advisor',
            safety_rules=[
                "Maintain a supportive, curious, and non-punitive tone at all times.",
                "Protect student privacy: Never include specific grades or full PII of other students.",
                "Avoid shaming or judgmental language; focus on growth and support.",
                "Provide at least one clear, actionable next step for the student.",
                "Always offer a 1-on-1 meeting link if the student's risk level is high.",
                "Keep messages concise, warm, and student-centered.",
            ],
        )
