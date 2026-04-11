from sqlmodel import SQLModel, Field, Relationship, Enum as SqlEnum
from datetime import datetime
from typing import Optional
from sqlalchemy import Index
from sqlalchemy import Column, JSON
import uuid
from enum import Enum

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"

class JobPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Job(SQLModel, table=True):
    
    id: int | None = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="jobs")
    type: str   
    payload: dict = Field(sa_column=Column(JSON))
    status: JobStatus = Field(
        sa_column= Column(
            SqlEnum(JobStatus, name="jobstatus"),
            default=JobStatus.QUEUED,
        ),
        default=JobStatus.QUEUED
    )
    priority:JobPriority = Field(
        sa_column= Column(
            SqlEnum(JobPriority, name="jobpriority"),
            default=JobPriority.LOW
        ),
        default=JobPriority.LOW 
    )
    attempts: int =Field(default=0) 
    max_retries: int = Field(default=3)
    worker_id: str | None = None
    lease_expires_at: datetime | None = None
    lease_token: str | None = None
    available_at: datetime | None = None
    
    last_heartbeat_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None   
    scheduled_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    __table_args__ = (
        Index("idx_job_status_scheduled", "status", "scheduled_at"),
    )