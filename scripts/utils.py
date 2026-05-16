import os
import sys
import functools
import logging
from src.core.config import config

logger = logging.getLogger(__name__)

def is_production():
    """Check if the current environment is production."""
    return config.environment == 'production'

def ensure_safe_environment(allow_prod=False):
    """
    Check if the environment is safe for destructive operations.
    If it's production and allow_prod is False, exit the script.
    """
    if is_production() and not allow_prod:
        print("\n" + "!" * 60)
        print("CRITICAL ERROR: THIS SCRIPT IS DESTRUCTIVE AND CANNOT RUN IN PRODUCTION.")
        print("To override this, ensure you are running in a non-production environment")
        print("or use the appropriate override flag if available.")
        print("!" * 60 + "\n")
        sys.exit(1)

def require_dev_only(func):
    """Decorator to restrict a function to non-production environments only."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if is_production():
            print(f"\nCRITICAL: {func.__name__} is restricted to development environments.")
            sys.exit(1)
        return await func(*args, **kwargs)
    return wrapper

def confirm_action(message="Are you sure you want to proceed?"):
    """Ask the user for confirmation before proceeding."""
    response = input(f"{message} [y/N]: ").lower()
    if response not in ('y', 'yes'):
        print("Action cancelled.")
        sys.exit(0)
