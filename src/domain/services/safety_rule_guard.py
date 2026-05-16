from typing import Protocol


class SafetyRuleGuard(Protocol):
    """Port for validating AI safety rules.

    This service ensures that safety rules provided by users or system defaults
    do not contain PII, prompt injections, or violate university tone policies.
    """

    def validate(self, rules: list[str]) -> None:
        """Validate a list of safety rules.

        Args:
            rules: The list of rules to validate.

        Raises:
            ValidationError: If any rule is found to be unsafe.
        """
        ...
