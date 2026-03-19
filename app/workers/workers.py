from app.queue.job_queue import JobQueue
from app.repository.job_repository import JobRepository
from sqlmodel import Session
from app.db.session import engine
from app.workers.dispatcher import Dispatcher
from app.services.job_services import JobService
import time
import uuid
import socket

def get_worker_id() -> str:
    """Generate a unique worker ID based on hostname and UUID"""
    hostname = socket.gethostname()
    unique_id = str(uuid.uuid4())[:8]
    return f"{hostname}_{unique_id}"

def run_worker():
    worker_id = get_worker_id()
    print(f"Worker started with ID: {worker_id}")
    
    while True:
        queue = JobQueue()
        repo = JobRepository()
        job_service = JobService(repo=repo, queue=queue)
        
        dispatcher = Dispatcher()
        ready_job_id = queue.pop_ready_job(now=time.time())
        if not ready_job_id:
            print("no job currently")
            time.sleep(1)
            continue
        with Session(engine) as session:
           job = repo.get_job(session, ready_job_id)
           job.worker_id = worker_id
           job.status = "running"
           repo.update_job(session, job)
           response = dispatcher.execute_job(job)
           if response != True and job.retries < job.max_retries:
               job_service.retry_job(session, job.id)
               
           elif response == True:
               repo.update_status(session, job.id, status="completed")
           else:                  
               repo.update_status(session, job.id, status="failed")

           
run_worker()        