"""
User management endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.async_database import get_db
from app.api.dependencies.auth import (
    get_current_active_user,
    get_current_admin_user,
    get_current_superadmin_user
)
from app.api.dependencies.pagination import get_pagination, get_search_params
from app.db.models.user import User
from app.db.models.enums import UserRole
from app.db.schemas.user import UserUpdate, UserResponse
from app.db.schemas.pagination import PaginationParams, SearchParams, PaginatedResponse
from app.services.user_service import user_service
from app.db.utils.user_crud import user_crud

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user information
    """
    return current_user


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    pagination: PaginationParams = Depends(get_pagination),
    search: SearchParams = Depends(get_search_params),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    email_verified: Optional[bool] = Query(None, description="Filter by email verification"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    List all users with search, filters, and pagination - Admin only

    Query parameters:
    - q: Search query (searches username, email, first_name, last_name)
    - role: Filter by user role
    - is_active: Filter by active status
    - email_verified: Filter by email verification status
    - sort_by: Field to sort by (id, username, email, created_at, last_login_at, role)
    - sort_order: Sort order (asc, desc)
    - page: Page number
    - page_size: Items per page
    """
    users, total = await user_crud.search(
        db=db,
        query=search.q,
        role=role,
        is_active=is_active,
        email_verified=email_verified,
        sort_by=search.sort_by,
        sort_order=search.sort_order or "asc",
        skip=pagination.skip,
        limit=pagination.limit
    )

    return PaginatedResponse.create(
        items=users,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.get("/role/{role}", response_model=PaginatedResponse[UserResponse])
async def list_users_by_role(
    role: UserRole,
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    List users by role with pagination - Admin only
    """
    users = await user_crud.get_by_role(
        db,
        role,
        skip=pagination.skip,
        limit=pagination.limit
    )
    total = await user_crud.count_by_role(db, role)

    return PaginatedResponse.create(
        items=users,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.get("/get/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user by ID
    """
    # Users can only view their own profile, admins can view anyone
    if current_user.id != user_id and not await user_crud.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )

    user = await user_service.get_user_by_id(db, user_id)
    return user


@router.put("/update/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update user by ID
    """
    # Users can only update their own profile, admins can update anyone
    if current_user.id != user_id and not await user_crud.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )

    # Prevent non-superadmin from updating roles
    if user_in.role is not None and not await user_crud.is_superadmin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can change user roles"
        )

    user = await user_service.update_user(db, user_id, user_in)
    return user


@router.put("/update/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    new_role: UserRole = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superadmin_user)
):
    """
    Update user role - Superadmin only
    """
    user = await user_service.update_user_role(db, user_id, new_role, current_user)
    return user


@router.delete("/delete/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Delete user by ID - Admin only
    """
    # Prevent deleting yourself
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    await user_service.delete_user(db, user_id)
    return {"message": "User deleted successfully"}
