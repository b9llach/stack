"""
Pagination dependencies
"""
from fastapi import Query
from typing import Optional

from app.db.schemas.pagination import PaginationParams, SearchParams


async def get_pagination(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
) -> PaginationParams:
    """
    Pagination dependency

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        PaginationParams instance
    """
    return PaginationParams(page=page, page_size=page_size)


async def get_search_params(
    q: Optional[str] = Query(None, min_length=1, max_length=100, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[str] = Query("asc", pattern="^(asc|desc)$", description="Sort order")
) -> SearchParams:
    """
    Search and filter dependency

    Args:
        q: Search query
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)

    Returns:
        SearchParams instance
    """
    return SearchParams(q=q, sort_by=sort_by, sort_order=sort_order)
