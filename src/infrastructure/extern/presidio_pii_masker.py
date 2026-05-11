from typing import ClassVar

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


class PresidioPiiMasker:
    """Production-grade PII redactor using Microsoft Presidio.

    This class leverages Natural Language Processing to identify and redact
    sensitive entities such as names, phone numbers, and emails.
    """

    _analyzer: ClassVar[AnalyzerEngine | None] = None
    _anonymizer: ClassVar[AnonymizerEngine | None] = None

    _OPERATORS: ClassVar[dict[str, OperatorConfig]] = {
        'PHONE_NUMBER': OperatorConfig('replace', {'new_value': '[REDACTED_PHONE]'}),
        'EMAIL_ADDRESS': OperatorConfig('replace', {'new_value': '[REDACTED_EMAIL]'}),
        'PERSON': OperatorConfig('replace', {'new_value': '[REDACTED_NAME]'}),
        'LOCATION': OperatorConfig('replace', {'new_value': '[REDACTED_LOCATION]'}),
        'URL': OperatorConfig('replace', {'new_value': '[REDACTED_URL]'}),
    }

    def __init__(self, language: str = 'en') -> None:
        """Initialize Presidio engines.

        Args:
            language: The language code for analysis (default: 'en').
        """
        if PresidioPiiMasker._analyzer is None:
            PresidioPiiMasker._analyzer = AnalyzerEngine()
        if PresidioPiiMasker._anonymizer is None:
            PresidioPiiMasker._anonymizer = AnonymizerEngine()
        self._language = language

    def mask(self, text: str) -> str:
        """Redact PII from the given text using NLP-based analysis.

        Args:
            text: The raw text to sanitize.

        Returns:
            The sanitized text with PII entities replaced by redaction markers.

        Raises:
            TypeError: If the input text is not a string.
        """
        if not text:
            return text

        # Identify sensitive entities
        results = self._analyzer.analyze(  # type: ignore
            text=text,
            language=self._language,
            entities=list(self._OPERATORS.keys()),
        )

        # Apply redaction
        anonymized_result = self._anonymizer.anonymize(  # type: ignore
            text=text,
            analyzer_results=results,
            operators=self._OPERATORS,
        )

        sanitized = anonymized_result.text

        # Invariant check: Output should not be empty if input was meaningful
        if text.strip() and not sanitized.strip():
            return '[REDACTION_FAILURE]'

        return sanitized
