from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Literal, Union, Any, Dict
import uuid


class JobResponse(BaseModel):
    """Response schema for job details"""
    id: int
    user_id: uuid.UUID
    type: str
    payload: Dict[str, Any]
    status: str
    priority: str
    retries: int
    max_retries: int
    worker_id: str | None
    scheduled_at: datetime | None
    created_at: datetime
    
    class Config:
        from_attributes = True


class EmailPayload(BaseModel):
    to: str | List[str]
    subject: str
    body: str | None = None
    template_id: str | None = None
    is_html: bool = False

class WebhookPayload(BaseModel):
    url: str
    method: Literal["GET", "POST", "PUT", "DELETE"] = "POST"
    data: Dict[str, Any] | None = None

class DataProcessingPayload(BaseModel):
    file_url: str
    operation: Literal["resize", "compress", "extract"]



class EmailJobCreateRequest(BaseModel):
    type: Literal["email"]
    payload: EmailPayload
    priority: str = "low"
    scheduled_at: datetime | None = None

class WebhookJobCreateRequest(BaseModel):
    type: Literal["webhook"]
    payload: WebhookPayload
    priority: str = "low"
    scheduled_at: datetime | None = None

class DataProcessingJobCreateRequest(BaseModel):
    type: Literal["data_processing"]
    payload: DataProcessingPayload
    priority: str = "low"
    scheduled_at: datetime | None = None

class GenericJobCreateRequest(BaseModel):
    type: str
    payload: Dict[str, Any]
    priority: str = "low"
    scheduled_at: datetime | None = None
    

 
JobCreateRequest = Union[
    EmailJobCreateRequest, 
    WebhookJobCreateRequest,
    DataProcessingJobCreateRequest,
    GenericJobCreateRequest
]