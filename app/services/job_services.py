from sqlmodel import Session
from app.models import Job
from app.utils.job_utils import exponential_backoff
from datetime import timedelta
class JobService:
    def __init__(self, repo, queue):
        self.repo = repo
        self.queue = queue
        
    def create_job(self, session:Session, job_data):
        job = self.repo.create_job(session, job_data)
        self.queue.enqueue(job.id, job_data.available_at)
        
        return job
    
    def retry_job(self, session:Session, job_id:str):
        job:Job = self.repo.get_job(session, job_id)
        
        if job and job.attempts < job.max_retries: 
            job.status = "queued"
            job.attempts = job.attempts + 1
            job.available_at = job.available_at + timedelta(seconds=exponential_backoff(job.attempts))
            job.worker_id = None
            job.lease_expires_at = None
            job.lease_token = None
            job.last_heartbeat_at = None
            job.started_at = None
            session.add(job)
            session.commit()
            session.refresh(job)
            
            
        
        
        return {
            "job_id": job.id if job else None,
            "available_at": job.available_at if job else None
        }
        
          
    
    