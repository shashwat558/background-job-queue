from sqlmodel import Session
from app.models.job import Job
from uuid import uuid4
from datetime import datetime, timedelta
import time
class JobRepository:
    
    def create_job(self, session: Session, job_data):
        job = job_data
        session.add(job)
        session.commit()
        session.refresh(job)
        
        return job
    
    def get_job(self, session:Session, job_id):
        job = session.get(Job, job_id)
        return job
    
    def update_status(self, session:Session, job_id, status):
        job = session.get(Job, job_id)
        
        if job:
            job.status = status
            session.add(job)
            session.commit()
            session.refresh(job)
        return job
    
    # def update_job(self, session:Session, job:Job):
    #     db_job = session.get(Job, job.id)
        
    #     if db_job:
    #         db_job.status = job.status
    #         db_job.attempts = job.attempts
    #         db_job.available_at = job.available_at
            
    #         session.add(db_job)
    #         session.commit()
    #         session.refresh(db_job)
        
    #     return db_job
    
    
    def try_claim_job(self, session:Session, job_id, worker_id, lease_duration, lease_token):
        job:Job = session.get(Job, job_id)
        if job and (job.status == "queued" or job.status == "retry_scheduled" or (job.lease_expires_at and job.lease_expires_at < datetime.now())):
            job.status = "running"
            job.worker_id = worker_id
            job.lease_expires_at = datetime.now() + timedelta(seconds=lease_duration)
            job.lease_token = lease_token
            job.attempts = job.attempts + 1
            job.last_heartbeat_at = datetime.now()
            job.started_at = datetime.now()
            session.add(job)
            session.commit()
            session.refresh(job)
            return {
                job_id: job.id,
                worker_id: job.worker_id,
                lease_duration: lease_duration,
                lease_token: job.lease_token
            }
        
        
        
    def complete_job(self, session:Session, job_id, worker_id, lease_token):
        job:Job = session.get(Job, job_id)
        if job and job.worker_id == worker_id and job.lease_token == lease_token and job.status == "running":
            job.status = "completed"
            job.completed_at = datetime.now()
            lease_token = None
            worker_id = None
            job.lease_expired_at = None
            session.add(job)
            session.commit()
            session.refresh(job)
            
            
        return job.id
    
    def mark_job_as_failed(self, session: Session, job_id, worker_id, lease_token):
        job:Job = session.get(Job, job_id)
        if job and job.worker_id == worker_id and job.lease_token == lease_token and job.status == "running":
            job.status = "failed"
            job.completed_at = datetime.now()
            lease_token = None
            worker_id = None
            job.lease_expired_at = None
            session.add(job)
            session.commit()
            session.refresh(job)
            
            
        return job.id
    
    def renew_lease(self, session:Session, job_id, worker_id, lease_token, LEASE_DURATION):
        job:Job = session.get(Job, job_id)
        if job and job.worker_id == worker_id and job.lease_token == lease_token and job.status == "running":
            job.last_heartbeat_at = datetime.now()
            job.lease_expires_at = datetime.now() + timedelta(seconds=LEASE_DURATION)
            session.add(job)
            session.commit()
            session.refresh(job)
            return True
        return False
        
    