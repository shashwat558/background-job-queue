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
        self.queue.enqueue(job.id, job_data.scheduled_at)
        
        return job
    
    def retry_job(self, session:Session, job_id:str):
        job:Job = self.repo.get_job(session, job_id)
        if job.retries == job.max_retries:
            return {"status": "failed"}
        retry_delay = exponential_backoff(job.retries)
        job.scheduled_at = job.scheduled_at + timedelta(seconds=retry_delay)
        job.retries = (job.retries + 1)
        
        job.status = "queued"
        updated_job = self.repo.update_job(session, job)
        self.queue.enqueue(job.id, job.scheduled_at)
        return updated_job
         
        
          
    
    