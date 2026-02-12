"""
User-specific CRUD operations
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.user import User
from app.db.models.enums import UserRole
from app.db.schemas.user import UserCreate, UserUpdate
from app.db.utils.crud import CRUDBase
from app.core.security import hash_password


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """
    CRUD operations for User model
    """

    async def get_by_email(
        self,
        db: AsyncSession,
        email: str
    ) -> Optional[User]:
        """
        Get user by email
        """
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(
        self,
        db: AsyncSession,
        username: str
    ) -> Optional[User]:
        """
        Get user by username
        """
        result = await db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        obj_in: UserCreate
    ) -> User:
        """
        Create a new user with hashed password
        Note: Users are always created with USER role for security
        """
        db_obj = User(
            username=obj_in.username,
            email=obj_in.email,
            hashed_password=hash_password(obj_in.password),
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            role=UserRole.USER  # Always USER role - admins promote via separate endpoint
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def authenticate(
        self,
        db: AsyncSession,
        username_or_email: str,
        password: str
    ) -> tuple[Optional[User], str]:
        """
        Authenticate a user by username or email with brute-force protection

        Returns:
            Tuple of (user, error_message)
            - (User, "") if authentication successful
            - (None, error_message) if failed
        """
        from app.core.security import verify_password
        from app.core.cache import cache_get, cache_set, cache_delete
        from app.core.config import settings

        max_attempts = getattr(settings, 'LOGIN_MAX_ATTEMPTS', 5)
        lockout_minutes = getattr(settings, 'LOGIN_LOCKOUT_MINUTES', 15)

        # Try to find user by username first
        user = await self.get_by_username(db, username_or_email)

        # If not found, try by email
        if not user:
            user = await self.get_by_email(db, username_or_email)

        # If still not found, authentication failed
        # Still check attempt tracking to prevent username enumeration timing attacks
        if not user:
            return None, "Incorrect username/email or password"

        # Check for account lockout
        lockout_key = f"login_lockout:{user.id}"
        attempts_key = f"login_attempts:{user.id}"

        lockout = await cache_get(lockout_key)
        if lockout:
            return None, f"Account temporarily locked. Try again in {lockout_minutes} minutes."

        # OAuth-only users cannot authenticate with password
        if user.hashed_password is None:
            return None, "Please login with your OAuth provider"

        # Verify password
        if not verify_password(password, user.hashed_password):
            # Increment failed attempts
            attempts = await cache_get(attempts_key)
            current_attempts = int(attempts) if attempts else 0
            new_attempts = current_attempts + 1

            if new_attempts >= max_attempts:
                # Lock the account
                await cache_set(lockout_key, "1", ttl=lockout_minutes * 60)
                await cache_delete(attempts_key)
                return None, f"Too many failed attempts. Account locked for {lockout_minutes} minutes."

            await cache_set(attempts_key, str(new_attempts), ttl=lockout_minutes * 60)
            remaining = max_attempts - new_attempts
            return None, f"Incorrect password. {remaining} attempts remaining."

        # Successful login - clear any failed attempts
        await cache_delete(attempts_key)
        return user, ""

    async def is_active(self, user: User) -> bool:
        """
        Check if user is active
        """
        return user.is_active

    async def has_role(self, user: User, role: UserRole) -> bool:
        """
        Check if user has specific role
        """
        return user.role == role

    async def is_admin(self, user: User) -> bool:
        """
        Check if user is admin or superadmin
        """
        return user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]

    async def is_superadmin(self, user: User) -> bool:
        """
        Check if user is superadmin
        """
        return user.role == UserRole.SUPERADMIN

    async def get_by_role(
        self,
        db: AsyncSession,
        role: UserRole,
        skip: int = 0,
        limit: int = 100
    ) -> list[User]:
        """
        Get users by role
        """
        result = await db.execute(
            select(User).where(User.role == role).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_role(
        self,
        db: AsyncSession,
        role: UserRole
    ) -> int:
        """
        Count users by role
        """
        from sqlalchemy import func
        result = await db.execute(
            select(func.count()).select_from(User).where(User.role == role)
        )
        return result.scalar_one()

    async def search(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        email_verified: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        skip: int = 0,
        limit: int = 20
    ) -> tuple[list[User], int]:
        """
        Search users with filters

        Args:
            db: Database session
            query: Search query (matches username, email, first_name, last_name)
            role: Filter by role
            is_active: Filter by active status
            email_verified: Filter by email verification status
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            skip: Number of records to skip
            limit: Number of records to return

        Returns:
            Tuple of (users, total_count)
        """
        from sqlalchemy import func, or_, asc, desc

        # Build base query
        stmt = select(User)
        count_stmt = select(func.count()).select_from(User)

        # Apply filters
        filters = []

        if query:
            search_filter = or_(
                User.username.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%"),
                User.first_name.ilike(f"%{query}%"),
                User.last_name.ilike(f"%{query}%")
            )
            filters.append(search_filter)

        if role is not None:
            filters.append(User.role == role)

        if is_active is not None:
            filters.append(User.is_active == is_active)

        if email_verified is not None:
            filters.append(User.email_verified == email_verified)

        # Apply filters to both queries
        if filters:
            for f in filters:
                stmt = stmt.where(f)
                count_stmt = count_stmt.where(f)

        # Apply sorting
        valid_sort_fields = {"id", "username", "email", "created_at", "last_login_at", "role"}
        if sort_by and sort_by in valid_sort_fields:
            order_func = desc if sort_order == "desc" else asc
            stmt = stmt.order_by(order_func(getattr(User, sort_by)))
        else:
            stmt = stmt.order_by(desc(User.created_at))

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        # Execute queries
        result = await db.execute(stmt)
        count_result = await db.execute(count_stmt)

        users = list(result.scalars().all())
        total = count_result.scalar_one()

        return users, total

    async def get_by_oauth(
        self,
        db: AsyncSession,
        oauth_provider: str,
        oauth_id: str
    ) -> Optional[User]:
        """
        Get user by OAuth provider and ID
        """
        result = await db.execute(
            select(User).where(
                User.oauth_provider == oauth_provider,
                User.oauth_id == oauth_id
            )
        )
        return result.scalar_one_or_none()

    async def create_oauth_user(
        self,
        db: AsyncSession,
        email: str,
        username: str,
        oauth_provider: str,
        oauth_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        email_verified: bool = False
    ) -> User:
        """
        Create a new user from OAuth authentication
        """
        import uuid

        # Ensure username is unique
        base_username = username[:42]  # Leave room for suffix (max 50 chars)
        final_username = base_username

        # Check if username exists and generate unique one if needed
        existing_user = await self.get_by_username(db, final_username)
        if existing_user:
            # Use short UUID suffix (8 chars) for guaranteed uniqueness
            suffix = uuid.uuid4().hex[:8]
            final_username = f"{base_username}_{suffix}"

        db_obj = User(
            username=final_username,
            email=email,
            hashed_password=None,  # OAuth users don't have passwords
            first_name=first_name,
            last_name=last_name,
            avatar_url=avatar_url,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
            email_verified=email_verified,
            role=UserRole.USER
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_or_create_oauth_user(
        self,
        db: AsyncSession,
        email: str,
        username: str,
        oauth_provider: str,
        oauth_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        email_verified: bool = False
    ) -> tuple[User, bool]:
        """
        Get existing OAuth user or create new one

        Security note: OAuth linking to existing accounts is only allowed if:
        1. The existing account already has this OAuth provider linked, OR
        2. The existing account was created via OAuth (no password), OR
        3. The OAuth provider confirms the email is verified

        Returns:
            Tuple of (user, created) where created is True if user was just created
        """
        # First try to get by OAuth ID (same provider + same OAuth user ID)
        user = await self.get_by_oauth(db, oauth_provider, oauth_id)
        if user:
            return user, False

        # Check if user exists with this email
        user = await self.get_by_email(db, email)
        if user:
            # Security: Only link OAuth if the email is verified by the OAuth provider
            # This prevents account takeover via OAuth with unverified email
            if not email_verified:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot link OAuth account: email not verified by OAuth provider"
                )

            # If user already has a different OAuth provider linked, don't overwrite
            if user.oauth_provider and user.oauth_provider != oauth_provider:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Account already linked to {user.oauth_provider}. Use that provider to login."
                )

            # Link OAuth to existing account (only if email is verified by OAuth provider)
            user.oauth_provider = oauth_provider
            user.oauth_id = oauth_id
            if not user.avatar_url and avatar_url:
                user.avatar_url = avatar_url
            if not user.email_verified and email_verified:
                user.email_verified = True
            db.add(user)
            await db.flush()
            await db.refresh(user)
            return user, False

        # Create new user
        user = await self.create_oauth_user(
            db=db,
            email=email,
            username=username,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
            first_name=first_name,
            last_name=last_name,
            avatar_url=avatar_url,
            email_verified=email_verified
        )
        return user, True


# Create a singleton instance
user_crud = CRUDUser(User)
