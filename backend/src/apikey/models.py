import datetime
from typing import List, Optional

from sqlalchemy import Index
from sqlmodel import Field, Relationship

from src.database import UTC_DATETIME, SQLModel
from src.user.models import UserDB
from src.utils import now


class ApiKeyDB(SQLModel, table=True):
    """API key model for authenticating API requests"""

    __table_args__ = (Index("ix_api_key_user_revoked", "user_id", "revoked"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    name: str = Field(default="", index=True)
    created_at: datetime.datetime = Field(default_factory=now, sa_type=UTC_DATETIME)
    last_used_at: Optional[datetime.datetime] = Field(default=None, sa_type=UTC_DATETIME)
    revoked: bool = Field(default=False)

    # User relationship
    user_id: int = Field(foreign_key="user.id")
    user: UserDB = Relationship(back_populates="api_keys")

    # Usage logs relationship
    usage_logs: List["ApiKeyUsageLogDB"] = Relationship(back_populates="api_key")


class ApiKeyUsageLogDB(SQLModel, table=True):
    """API key usage log model for tracking API usage"""

    __table_args__ = (
        Index(
            "ix_api_key_usage_log_key_timestamp_status",
            "api_key_id",
            "timestamp",
            "status_code",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime.datetime = Field(default_factory=now, sa_type=UTC_DATETIME)
    endpoint: str = Field(index=True)
    method: str
    model: Optional[str] = Field(default=None)
    status_code: int

    # API key relationship
    api_key_id: int = Field(foreign_key="api_key.id")
    api_key: ApiKeyDB = Relationship(back_populates="usage_logs")
