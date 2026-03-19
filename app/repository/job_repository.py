from sqlmodel import Session
from app.models.job import Job
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
    
    def update_job(self, session:Session, job:Job):
        db_job = session.get(Job, job.id)
        
        if db_job:
            db_job.status = job.status
            db_job.retries = job.retries
            db_job.scheduled_at = job.scheduled_at
            session.add(db_job)
            session.commit()
            session.refresh(db_job)
        
        return db_job  
        
        