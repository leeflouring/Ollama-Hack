from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, Relationship

from src.ai_model.models import AIModelDB, EndpointAIModelDB
from src.database import UTC_DATETIME, SQLModel
from src.utils import now


class EndpointStatusEnum(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    FAKE = "fake"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class EndpointDB(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True, index=True)
    name: str = Field(index=True)
    created_at: datetime = Field(default_factory=now, sa_type=UTC_DATETIME)
    status: EndpointStatusEnum = Field(default=EndpointStatusEnum.UNAVAILABLE)

    ai_models: list["AIModelDB"] = Relationship(
        back_populates="endpoints",
        link_model=EndpointAIModelDB,
    )
    performances: list["EndpointPerformanceDB"] = Relationship(
        back_populates="endpoint",
        sa_relationship_kwargs={
            "order_by": "EndpointPerformanceDB.created_at.desc()",
            "cascade": "all, delete-orphan",
        },
    )

    ai_model_links: list["EndpointAIModelDB"] = Relationship(
        back_populates="endpoint",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    test_tasks: list["EndpointTestTask"] = Relationship(
        back_populates="endpoint",
        sa_relationship_kwargs={
            "order_by": "EndpointTestTask.created_at.desc()",
            "cascade": "all, delete-orphan",
        },
    )


class EndpointPerformanceDB(SQLModel, table=True):
    __table_args__ = (
        Index("ix_endpoint_performance_endpoint_created", "endpoint_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    status: EndpointStatusEnum = Field(default=EndpointStatusEnum.UNAVAILABLE)
    ollama_version: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=now, sa_type=UTC_DATETIME)

    endpoint_id: Optional[int] = Field(foreign_key="endpoint.id", default=None)

    endpoint: EndpointDB = Relationship(back_populates="performances")


class EndpointTestTask(SQLModel, table=True):
    __table_args__ = (
        Index("ix_endpoint_test_task_endpoint_scheduled", "endpoint_id", "scheduled_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    endpoint_id: int = Field(foreign_key="endpoint.id")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    scheduled_at: datetime = Field(default_factory=now, sa_type=UTC_DATETIME)
    last_tried: Optional[datetime] = Field(default=None, sa_type=UTC_DATETIME)
    created_at: datetime = Field(default_factory=now, sa_type=UTC_DATETIME)

    endpoint: EndpointDB = Relationship(back_populates="test_tasks")
