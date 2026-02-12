"""
Database enums
"""
import enum


class UserRole(str, enum.Enum):
    """
    User role enumeration
    """
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"

    def __str__(self):
        return self.value
