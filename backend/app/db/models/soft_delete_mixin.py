"""
Soft delete mixin for models
"""
from sqlalchemy import Column, Boolean, DateTime
from sqlalchemy.sql import func


class SoftDeleteMixin:
    """
    Mixin to add soft delete functionality to models

    Usage:
        class MyModel(Base, SoftDeleteMixin):
            __tablename__ = "my_table"
            ...
    """
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def soft_delete(self):
        """Mark record as deleted"""
        self.is_deleted = True
        self.deleted_at = func.now()

    def restore(self):
        """Restore soft-deleted record"""
        self.is_deleted = False
        self.deleted_at = None
