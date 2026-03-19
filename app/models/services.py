from sqlmodel import SQLModel, Field, Relationship, Column, Enum as SqlEnum
from typing import Optional
from datetime import datetime
import uuid
from enum import Enum

class NameOfServices(str, Enum):
    EMAIL= "email"

class Service(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: NameOfServices = Field(
        sa_column= Column(
            SqlEnum(NameOfServices, name="nameofservices"),
            default=NameOfServices.EMAIL,
        ),
        default=NameOfServices.EMAIL,

    )
    user_id: uuid.UUID = Field(foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="services")
    api_key: str