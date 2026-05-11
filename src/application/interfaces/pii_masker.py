from typing import Protocol


class PiiMasker(Protocol):
    """Port for redacting PII from text."""

    def mask(self, text: str) -> str:
        """Redact PII from the given text.

        Args:
            text: The text to sanitize.

        Returns:
            The sanitized text.
        """
        ...
