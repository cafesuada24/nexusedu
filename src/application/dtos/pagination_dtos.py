"""DTOs for pagination results."""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

@dataclass
class PaginationMetadata:
    """Metadata for paged results."""
    total_count: int
    limit: int
    offset: int
    has_next: bool

@dataclass
class PagedResult(Generic[T]):
    """Unified response structure for paginated lists."""
    items: list[T]
    metadata: PaginationMetadata
