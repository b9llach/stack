"""
Audit log model for tracking changes
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func

from app.core.async_database import Base


class AuditLog(Base):
    """
    Audit log for tracking user actions
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)  # Who made the change
    username = Column(String(50))
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, etc.
    entity_type = Column(String(50))  # User, Product, Order, etc.
    entity_id = Column(Integer)  # ID of the affected entity
    changes = Column(JSON)  # JSON of what changed (old_value, new_value)
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)
    correlation_id = Column(String(36))  # For request tracing
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user={self.username}, action={self.action}, entity={self.entity_type})>"
