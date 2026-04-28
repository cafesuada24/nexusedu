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
    """Get an environment variable."""
    if value := os.getenv(key):
        return value

    if (
        required_in_production
        and os.getenv('ENVIRONMENT', 'production').lower() == 'production'
    ):
        raise ValueError(f'{key} variable is required in production environment')

    return default
