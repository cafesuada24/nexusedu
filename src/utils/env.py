"""Environment variable utilities."""

import os
from typing import overload

from dotenv import load_dotenv

load_dotenv()


@overload
def getenv(
    key: str,
    default: str,
    *,
    required_in_production: bool = True,
) -> str: ...


@overload
def getenv(
    key: str,
    default: None = None,
    *,
    required_in_production: bool = True,
) -> str | None: ...


def getenv(
    key: str,
    default: str | None = None,
    *,
    required_in_production: bool = True,
) -> str | None:
    """Get an environment variable with optional production requirement check.

    Args:
        key: The name of the environment variable.
        default: The default value to return if the variable is not set.
        required_in_production: If True, raises ValueError in production if not set.

    Returns:
        The value of the environment variable or the default.

    Raises:
        ValueError: If the variable is required in production but not set.
    """
    if value := os.getenv(key):
        return value

    if (
        required_in_production
        and os.getenv('ENVIRONMENT', 'production').lower() == 'production'
    ):
        raise ValueError(f'{key} variable is required in production environment')

    return default
