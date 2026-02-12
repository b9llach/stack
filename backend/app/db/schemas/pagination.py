"""
Pagination schemas for list responses
"""
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List, Optional
from math import ceil

T = TypeVar("T")


class PaginationParams(BaseModel):
    """
    Pagination parameters
    """
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")

    @property
    def skip(self) -> int:
        """Calculate offset for database query"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Alias for page_size"""
        return self.page_size


class PaginationMeta(BaseModel):
    """
    Pagination metadata
    """
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper
    """
    items: List[T] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResponse[T]":
        """
        Create a paginated response

        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number
            page_size: Items per page

        Returns:
            PaginatedResponse instance
        """
        total_pages = ceil(total / page_size) if page_size > 0 else 0

        return cls(
            items=items,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1
            )
        )


class SearchParams(BaseModel):
    """
    Search and filter parameters
    """
    q: Optional[str] = Field(None, description="Search query", min_length=1, max_length=100)
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$", description="Sort order (asc/desc)")
