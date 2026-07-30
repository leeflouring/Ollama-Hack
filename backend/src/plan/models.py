import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship

from src.database import UTC_DATETIME, SQLModel
from src.user.models import UserDB
from src.utils import now


class PlanDB(SQLModel, table=True):
    """
    Plan model for user subscription plans with rate limits
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str = Field(default="")
    rpm: int = Field(default=60, description="Requests per minute limit")
    rpd: int = Field(default=10000, description="Requests per day limit")
    is_default: bool = Field(
        default=False,
        index=True,
        description="Whether this is the default plan for new users",
    )
    created_at: datetime.datetime = Field(default_factory=now, sa_type=UTC_DATETIME)
    updated_at: datetime.datetime = Field(default_factory=now, sa_type=UTC_DATETIME)

    # Relationships
    users: List["UserDB"] = Relationship(back_populates="plan")
