import re
import structlog

from src.application.interfaces.pii_masker import PiiMasker
from src.domain.exceptions import ValidationError

logger = structlog.get_logger(__name__)


class GuardrailsSafetyRuleGuard:
    """Implementation of SafetyRuleGuard using PII masking and heuristics.

    This service identifies PII leaks and common prompt injection patterns
    to ensure safety rules are secure before being stored.
    """

    def __init__(self, pii_masker: PiiMasker) -> None:
        self._pii_masker = pii_masker
        # Patterns for prompt injection detection
        self._injection_patterns = [
            re.compile(r'ignore\s+.*instructions', re.IGNORECASE),
            re.compile(r'system\s+prompt', re.IGNORECASE),
            re.compile(r'override', re.IGNORECASE),
            re.compile(r'you\s+are\s+now', re.IGNORECASE),
            re.compile(r'acting\s+as', re.IGNORECASE),
            re.compile(r'forget\s+your', re.IGNORECASE),
            re.compile(r'bypass', re.IGNORECASE),
        ]

    def validate(self, rules: list[str]) -> None:
        """Validate safety rules for PII and injections."""
        for rule in rules:
            self._check_pii(rule)
            self._check_injection(rule)

    def _check_pii(self, rule: str) -> None:
        """Check for PII in a single rule."""
        masked = self._pii_masker.mask(rule)
        # If the masker changed the text, it detected something
        if masked != rule:
            logger.warning('PII detected in safety rule', rule=rule)
            raise ValidationError(
                f'Rule contains potential PII or sensitive data: "{rule}"'
            )

    def _check_injection(self, rule: str) -> None:
        """Check for prompt injection patterns."""
        for pattern in self._injection_patterns:
            if pattern.search(rule):
                logger.warning('Prompt injection detected in safety rule', rule=rule)
                raise ValidationError(
                    f'Rule contains disallowed instruction-override patterns: "{rule}"'
                )
