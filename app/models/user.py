from sqlmodel import SQLModel, Field, Relationship, Column, Enum as SqlEnum
from datetime import datetime
import uuid
from typing import Optional, List
from .job import Job
from .services import Service
from enum import Enum

class Provider(str, Enum):
    GOOGLE = "google"
    CREDENTIALS = "credentials"


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(nullable=False, unique=True)
    hashed_password: Optional[str]
    google_id: Optional[str] = Field(unique=True)
    avatar_url: Optional[str]
    is_active: bool = Field(default=False)
    is_verified: Optional[bool] = Field(default=False)
    provider: Provider = Field(
        sa_column= Column(
            SqlEnum(Provider, name="provider"),
            default=Provider.CREDENTIALS,
        ),
        default=Provider.CREDENTIALS,
    ) 
    jobs: List["Job"] = Relationship(back_populates="user")
    services: List["Service"] = Relationship(back_populates="user")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    
    