import uuid

import uuid6

type EntityID = uuid.UUID


def generate_uuid() -> EntityID:
    """Generate a UUIDv7 for use as a primary key or unique identifier.

    This centralizes UUID generation to allow for easier migration to other
    identifier formats in the future.
    """
    return uuid6.uuid7()
