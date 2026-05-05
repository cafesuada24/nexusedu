"""Pagination DTOs."""

from pydantic import BaseModel, Field, NonNegativeInt


class PaginationMetadata(BaseModel):
    """Metadata for paged results."""

    total_count: NonNegativeInt = Field(..., description='Total number of items available.')
    limit: NonNegativeInt = Field(..., description='Number of items per page.')
    offset: NonNegativeInt = Field(..., description='Number of items skipped.')
    has_next: bool = Field(..., description='True if there are more pages.')


class PagedResponse[T](BaseModel):
    """A paged response."""

    items: list[T]
    metadata: PaginationMetadata
