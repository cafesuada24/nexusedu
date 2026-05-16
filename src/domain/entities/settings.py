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
    def create_default(cls, user_id: UUID) -> 'UserSettings':
        """Create default settings for a new user."""
        return cls(
            user_id=user_id,
            auto_draft_enabled=True,
            ai_tone='warm',
            signature=None,
            safety_rules=[
                "Không tiết lộ điểm số của sinh viên khác",
                "Luôn gọi sinh viên theo đúng tên và đại từ đã khai báo",
                "Không dùng ngôn ngữ đe doạ hay phán xét",
                "Luôn đề xuất ít nhất 1 hành động cụ thể sinh viên có thể làm",
                "Luôn kèm link đặt lịch 1-1 nếu mức rủi ro > trung bình",
                "Không gửi quá 2 email/tuần cho cùng một sinh viên",
            ],
        )
