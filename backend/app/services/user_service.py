"""
User service for business logic
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.db.models.user import User
from app.db.models.enums import UserRole
from app.db.schemas.user import UserCreate, UserUpdate, UserResponse
from app.db.utils.user_crud import user_crud
from app.core.security import create_access_token, create_refresh_token
from app.utils.validators import validate_password_strength


class UserService:
    """
    Service class for user-related business logic
    """

    async def create_user(
        self,
        db: AsyncSession,
        user_in: UserCreate
    ) -> User:
        """
        Create a new user

        Args:
            db: Database session
            user_in: User creation data

        Returns:
            Created user

        Raises:
            HTTPException: If username or email already exists, or password is weak
        """
        # Validate password strength
        is_valid, error_message = validate_password_strength(user_in.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

        # Check if username exists
        existing_user = await user_crud.get_by_username(db, user_in.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        # Check if email exists
        existing_email = await user_crud.get_by_email(db, user_in.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create user
        user = await user_crud.create(db, user_in)
        await db.commit()
        return user

    async def authenticate_user(
        self,
        db: AsyncSession,
        username_or_email: str,
        password: str
    ) -> dict:
        """
        Authenticate user and return tokens

        Args:
            db: Database session
            username_or_email: Username or email address
            password: Password

        Returns:
            Dictionary with access and refresh tokens

        Raises:
            HTTPException: If authentication fails
        """
        user, error_message = await user_crud.authenticate(db, username_or_email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_message or "Incorrect username/email or password"
            )

        if not await user_crud.is_active(user):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        # Create tokens with role information
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "username": user.username,
                "role": user.role.value
            }
        )
        refresh_token = create_refresh_token(
            data={
                "sub": str(user.id),
                "username": user.username,
                "role": user.role.value
            }
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    async def get_user_by_id(
        self,
        db: AsyncSession,
        user_id: int
    ) -> User:
        """
        Get user by ID

        Args:
            db: Database session
            user_id: User ID

        Returns:
            User object

        Raises:
            HTTPException: If user not found
        """
        user = await user_crud.get(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    async def get_users(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Get list of users

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of users
        """
        users = await user_crud.get_multi(db, skip=skip, limit=limit)
        return users

    async def update_user(
        self,
        db: AsyncSession,
        user_id: int,
        user_in: UserUpdate
    ) -> User:
        """
        Update user

        Args:
            db: Database session
            user_id: User ID
            user_in: User update data

        Returns:
            Updated user

        Raises:
            HTTPException: If user not found
        """
        user = await self.get_user_by_id(db, user_id)
        user = await user_crud.update(db, user, user_in)
        await db.commit()
        return user

    async def delete_user(
        self,
        db: AsyncSession,
        user_id: int
    ) -> None:
        """
        Delete user

        Args:
            db: Database session
            user_id: User ID

        Raises:
            HTTPException: If user not found
        """
        user = await user_crud.delete(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        await db.commit()

    async def get_users_by_role(
        self,
        db: AsyncSession,
        role: UserRole,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Get users by role

        Args:
            db: Database session
            role: User role to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of users with specified role
        """
        users = await user_crud.get_by_role(db, role, skip=skip, limit=limit)
        return users

    async def update_user_role(
        self,
        db: AsyncSession,
        user_id: int,
        new_role: UserRole,
        requester: User
    ) -> User:
        """
        Update user role (restricted to superadmin)

        Args:
            db: Database session
            user_id: User ID to update
            new_role: New role to assign
            requester: User making the request

        Returns:
            Updated user

        Raises:
            HTTPException: If requester is not superadmin or user not found
        """
        # Only superadmin can change roles
        if not await user_crud.is_superadmin(requester):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin can change user roles"
            )

        user = await self.get_user_by_id(db, user_id)

        # Update role
        user_update = UserUpdate(role=new_role)
        user = await user_crud.update(db, user, user_update)
        await db.commit()

        return user


# Create singleton instance
user_service = UserService()
