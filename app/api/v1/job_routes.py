from fastapi import APIRouter, HTTPException, Depends
from app.schemas.job import JobCreateRequest, JobResponse
from app.services.job_services import JobService
from app.repository.job_repository import JobRepository
from app.queue.job_queue import JobQueue
from app.api.deps import get_current_user
from app.models.job import Job
from app.db.session import get_session
from sqlmodel import Session
router = APIRouter()

@router.post("/create")
async def create_job(data:JobCreateRequest, current_user:str = Depends(get_current_user), session:Session = Depends(get_session)):
    repo = JobRepository()
    queue = JobQueue()
    job = Job(
        type=data.type,
        priority=data.priority,
        scheduled_at=data.scheduled_at,
        available_at= data.scheduled_at,
        user_id= current_user,
        payload=data.payload.model_dump()
    )
    service = JobService(repo=repo, queue=queue)
    created_job = service.create_job(session=session, job_data=job)
    return created_job
    
    
    
    
    
    
    
    
    
    

