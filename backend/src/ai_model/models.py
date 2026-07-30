from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index
from sqlmodel import Column, Field, Relationship

from src.database import LONGTEXT, UTC_DATETIME, SQLModel
from src.utils import now

if TYPE_CHECKING:
    from src.endpoint.models import EndpointDB


class AIModelStatusEnum(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    FAKE = "fake"
    MISSING = "missing"


class EndpointAIModelDB(SQLModel, table=True):
    __table_args__ = (
        Index("ix_endpoint_ai_model_endpoint_status", "endpoint_id", "status"),
        Index("ix_endpoint_ai_model_model_status", "ai_model_id", "status"),
    )

    endpoint_id: int = Field(foreign_key="endpoint.id", primary_key=True)
    ai_model_id: int = Field(foreign_key="ai_model.id", primary_key=True)

    status: AIModelStatusEnum = Field(default=AIModelStatusEnum.MISSING)
    token_per_second: float = Field(default=0)
    max_connection_time: float = Field(default=60)

    performances: list["AIModelPerformanceDB"] = Relationship(
        back_populates="link",
        sa_relationship_kwargs={
            "primaryjoin": "and_(EndpointAIModelDB.endpoint_id == foreign(AIModelPerformanceDB.endpoint_id), "
            "EndpointAIModelDB.ai_model_id == foreign(AIModelPerformanceDB.ai_model_id))",
            "foreign_keys": "[AIModelPerformanceDB.endpoint_id, AIModelPerformanceDB.ai_model_id]",
            "cascade": "all, delete-orphan",
        },
    )

    endpoint: "EndpointDB" = Relationship(back_populates="ai_model_links")
    ai_model: "AIModelDB" = Relationship(back_populates="endpoint_links")


class AIModelDB(SQLModel, table=True):
    __table_args__ = (Index("ix_ai_model_name_tag", "name", "tag"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # deepseek-r1
    tag: str = Field(index=True)  # 32b
    created_at: datetime = Field(default_factory=now, sa_type=UTC_DATETIME)

    endpoint_links: list["EndpointAIModelDB"] = Relationship(
        back_populates="ai_model",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    endpoints: list["EndpointDB"] = Relationship(
        back_populates="ai_models",
        link_model=EndpointAIModelDB,
    )


class AIModelPerformanceDB(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    status: AIModelStatusEnum = Field(default=AIModelStatusEnum.MISSING)
    token_per_second: float = Field(default=0)
    connection_time: float = Field(
        default=60, description="The time from the request to the first response"
    )
    total_time: float = Field(default=120, description="The total time of the request")
    output: str = Field(default="", sa_column=Column(LONGTEXT))
    output_tokens: int = Field(default=0)
    created_at: datetime = Field(default_factory=now, sa_type=UTC_DATETIME)

    endpoint_id: Optional[int] = Field(default=None, foreign_key="endpoint.id")
    ai_model_id: Optional[int] = Field(default=None, foreign_key="ai_model.id")

    link: "EndpointAIModelDB" = Relationship(
        back_populates="performances",
        sa_relationship_kwargs={
            "primaryjoin": "and_(AIModelPerformanceDB.endpoint_id == remote(EndpointAIModelDB.endpoint_id), "
            "AIModelPerformanceDB.ai_model_id == remote(EndpointAIModelDB.ai_model_id))",
            "foreign_keys": "[AIModelPerformanceDB.endpoint_id, AIModelPerformanceDB.ai_model_id]",
        },
    )
