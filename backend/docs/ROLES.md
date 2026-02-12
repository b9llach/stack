# Role-Based Access Control (RBAC)

This FastAPI template implements a hierarchical role-based access control system with three distinct roles: **User**, **Admin**, and **Superadmin**.

## Table of Contents
- [Overview](#overview)
- [Role Hierarchy](#role-hierarchy)
- [Role Definitions](#role-definitions)
- [Implementation](#implementation)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)

## Overview

The RBAC system is implemented using:
- **SQLAlchemy Enum**: `UserRole` enum in `app/db/models/enums.py`
- **FastAPI Dependencies**: Role-checking functions in `app/api/dependencies/auth.py`
- **Database Column**: `role` column in the User model

Every user is assigned exactly one role, which determines their permissions throughout the application.

## Role Hierarchy

```
SUPERADMIN (Highest)
    ↓
  ADMIN
    ↓
  USER (Default)
```

Higher roles inherit all permissions from lower roles.

## Role Definitions

### USER (Default Role)

**Default role** assigned to all new users during registration.

**Permissions:**
- View own profile (`GET /api/v1/users/me`)
- Update own profile (`PUT /api/v1/users/update/{user_id}` - self only)
- Enable/disable 2FA for own account
- Access public endpoints
- Use WebSocket connections

**Cannot:**
- View other users' profiles
- Manage other users
- Change any user roles
- Access admin-only endpoints

**Use Cases:**
- Regular application users
- Customer accounts
- Basic authenticated access

---

### ADMIN

**Elevated role** for managing users and application resources.

**Permissions:**
- **All USER permissions** (inherited)
- View all users (`GET /api/v1/users/`)
- View users by role (`GET /api/v1/users/role/{role}`)
- View any user profile (`GET /api/v1/users/get/{user_id}`)
- Update any user profile (`PUT /api/v1/users/update/{user_id}`)
- Delete users (`DELETE /api/v1/users/delete/{user_id}`)
- Manage user accounts (activate/deactivate)

**Cannot:**
- Change user roles (including their own)
- Access superadmin-only endpoints

**Use Cases:**
- Customer support staff
- Content moderators
- User account managers

---

### SUPERADMIN (Highest Role)

**Highest privilege role** with full system access.

**Permissions:**
- **All ADMIN permissions** (inherited)
- **All USER permissions** (inherited)
- Change user roles (`PUT /api/v1/users/update/{user_id}/role`)
- Promote users to ADMIN or SUPERADMIN
- Demote users to lower roles
- Full system configuration access

**Use Cases:**
- System administrators
- Application owners
- DevOps team members

---

## Implementation

### Database Model

**File:** `app/db/models/enums.py`

```python
import enum

class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"
```

**File:** `app/db/models/user.py`

```python
from app.db.models.enums import UserRole

class User(Base):
    # ...
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
```

### CRUD Operations

**File:** `app/db/utils/user_crud.py`

```python
async def is_admin(self, user: User) -> bool:
    """Check if user is admin or superadmin"""
    return user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]

async def is_superadmin(self, user: User) -> bool:
    """Check if user is superadmin"""
    return user.role == UserRole.SUPERADMIN

async def has_role(self, user: User, required_role: UserRole) -> bool:
    """Check if user has at least the required role level"""
    role_hierarchy = {
        UserRole.USER: 1,
        UserRole.ADMIN: 2,
        UserRole.SUPERADMIN: 3
    }
    return role_hierarchy.get(user.role, 0) >= role_hierarchy.get(required_role, 0)
```

### Authentication Dependencies

**File:** `app/api/dependencies/auth.py`

```python
from fastapi import Depends, HTTPException, status
from app.db.models.user import User
from app.db.models.enums import UserRole

# Get current authenticated user
async def get_current_active_user(...) -> User:
    # Returns current user or raises 401

# Require admin or superadmin
async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if not await user_crud.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin role required."
        )
    return current_user

# Require superadmin
async def get_current_superadmin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if not await user_crud.is_superadmin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Superadmin role required."
        )
    return current_user

# Flexible role checker
def require_role(required_role: UserRole):
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if not await user_crud.has_role(current_user, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. {required_role.value} role required."
            )
        return current_user
    return role_checker
```

## Usage Examples

### 1. User-Only Endpoint

Any authenticated user can access:

```python
from app.api.dependencies.auth import get_current_active_user

@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_active_user)
):
    return {"user": current_user.username, "role": current_user.role}
```

### 2. Admin-Only Endpoint

Only admins and superadmins can access:

```python
from app.api.dependencies.auth import get_current_admin_user

@router.get("/users")
async def list_all_users(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    users = await user_crud.get_all(db)
    return users
```

### 3. Superadmin-Only Endpoint

Only superadmins can access:

```python
from app.api.dependencies.auth import get_current_superadmin_user

@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: int,
    new_role: UserRole,
    current_user: User = Depends(get_current_superadmin_user),
    db: AsyncSession = Depends(get_db)
):
    user = await user_crud.get_by_id(db, user_id)
    user.role = new_role
    await db.commit()
    return {"message": f"User role updated to {new_role.value}"}
```

### 4. Custom Role Requirement

Using the flexible `require_role` dependency:

```python
from app.api.dependencies.auth import require_role
from app.db.models.enums import UserRole

@router.post("/moderate-content")
async def moderate_content(
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    # Only ADMIN and SUPERADMIN can access
    return {"message": "Content moderated"}
```

### 5. Self-or-Admin Access

Allow users to access their own data, or admins to access anyone's:

```python
from app.api.dependencies.auth import get_current_active_user

@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if user is accessing their own data or is an admin
    if current_user.id != user_id and not await user_crud.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own profile"
        )

    user = await user_crud.get_by_id(db, user_id)
    return user
```

## Best Practices

### 1. Principle of Least Privilege

Always assign the minimum role required:

```python
# Good: Default to USER role
new_user.role = UserRole.USER

# Bad: Don't default to ADMIN
new_user.role = UserRole.ADMIN  # Never do this
```

### 2. Validate Role Changes

When changing roles, verify the requester has sufficient permissions:

```python
@router.put("/users/{user_id}/role")
async def update_role(
    user_id: int,
    new_role: UserRole,
    current_user: User = Depends(get_current_superadmin_user),  # Only superadmin
    db: AsyncSession = Depends(get_db)
):
    # Superadmins verified by dependency
    target_user = await user_crud.get_by_id(db, user_id)
    target_user.role = new_role
    await db.commit()
    return {"message": "Role updated"}
```

### 3. Don't Hardcode Role Checks

Use the provided dependencies instead of manual checks:

```python
# Good: Use dependency
@router.get("/admin-panel")
async def admin_panel(
    current_user: User = Depends(get_current_admin_user)
):
    return {"message": "Welcome admin"}

# Bad: Manual role check
@router.get("/admin-panel")
async def admin_panel(
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != UserRole.ADMIN:  # Fragile, easy to forget
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"message": "Welcome admin"}
```

### 4. Log Role Changes

Always log when user roles are modified:

```python
import logging

logger = logging.getLogger(__name__)

@router.put("/users/{user_id}/role")
async def change_role(user_id: int, new_role: UserRole, ...):
    old_role = user.role
    user.role = new_role

    logger.warning(
        f"Role changed: User {user_id} ({user.username}) "
        f"from {old_role.value} to {new_role.value} "
        f"by {current_user.username}"
    )

    await db.commit()
    return {"message": "Role updated"}
```

### 5. Protect Role Field in Updates

Prevent users from changing their own role via profile update:

```python
@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Don't allow role updates via this endpoint
    if user_update.role is not None:
        # Only superadmins can change roles, and only via dedicated endpoint
        if not await user_crud.is_superadmin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role changes must be done via /users/{id}/role endpoint"
            )

    # ... update logic
```

## API Endpoints by Role

### Public (No Auth)
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/verify-2fa` - Verify 2FA code
- `GET /api/v1/health/*` - Health checks

### USER (Authenticated)
- `GET /api/v1/users/me` - Get own profile
- `PUT /api/v1/users/update/{user_id}` - Update own profile (self only)
- `POST /api/v1/auth/enable-2fa` - Enable 2FA for self
- `POST /api/v1/auth/disable-2fa` - Disable 2FA for self
- `POST /api/v1/auth/test-2fa` - Test 2FA email

### ADMIN (+ all USER permissions)
- `GET /api/v1/users/` - List all users
- `GET /api/v1/users/role/{role}` - List users by role
- `GET /api/v1/users/get/{user_id}` - Get any user profile
- `PUT /api/v1/users/update/{user_id}` - Update any user profile
- `DELETE /api/v1/users/delete/{user_id}` - Delete users

### SUPERADMIN (+ all ADMIN permissions)
- `PUT /api/v1/users/update/{user_id}/role` - Change user roles

## Security Considerations

1. **First Superadmin**: Create using `setup_first_superadmin.py` script
2. **Role Escalation**: Never allow users to self-promote
3. **Audit Trail**: Log all role changes for security audits
4. **Token Claims**: User role is included in JWT tokens
5. **Re-authentication**: Consider requiring re-authentication for sensitive operations

## Troubleshooting

### Issue: "Insufficient permissions" error

**Cause**: User doesn't have required role

**Solution**:
1. Check current user role: `GET /api/v1/users/me`
2. If needed, have a superadmin promote you: `PUT /api/v1/users/update/{id}/role`

### Issue: Can't create first superadmin

**Cause**: No existing superadmin to promote users

**Solution**: Use the setup script:
```bash
python setup_first_superadmin.py
```

### Issue: Admin can't change roles

**Cause**: Only superadmins can change roles

**Solution**: This is by design. Contact a superadmin or use the setup script if no superadmin exists.

---

**Related Documentation:**
- [User Settings](USER_SETTINGS.md) - User profile and 2FA management
- [Email Setup](EMAIL_SETUP.md) - Email configuration for notifications
