from app.queue.job_queue import JobQueue
from app.repository.job_repository import JobRepository
from sqlmodel import Session
from app.db.session import engine
from app.workers.dispatcher import Dispatcher
from app.services.job_services import JobService
import time
import uuid
import socket
from datetime import datetime, timedelta
from app.core.config import LEASE_DURATION
import threading

def get_worker_id() -> str:
    """Generate a unique worker ID based on hostname and UUID"""
    hostname = socket.gethostname()
    unique_id = str(uuid.uuid4())[:8]
    return f"{hostname}_{unique_id}"

def get_unique_lease_id() -> str:
    "Generate a unique lease token"
    return str(uuid.uuid4())[:8]


def run_worker():
    worker_id = get_worker_id()
    lease_token = get_unique_lease_id()
    print(f"Worker started with ID: {worker_id}")
    stop_event = threading.Event()
    
    def heartbeat_loop(job_id, lease_token , worker_id):
        while not stop_event.is_set():
            time.sleep(LEASE_DURATION / 3)
            success = repo.renew_lease(session, job_id, worker_id, lease_token, LEASE_DURATION)
            if not success:
                
                print("Lost lease, stopping job")
                stop_event.set()
                break

    hb_thread = threading.Thread(target=heartbeat_loop, args=(job.id, job.lease_token, worker_id), daemon=True)
    while True:
        queue = JobQueue()
        repo = JobRepository()
        job_service = JobService(repo=repo, queue=queue)
        
        dispatcher = Dispatcher()
        ready_job_id = queue.get_ready_job_id(now=time.time())
        if not ready_job_id:
            print("no job currently")
            time.sleep(1)
            continue
        with Session(engine) as session:
           
           job = repo.try_claim_job(session, ready_job_id, worker_id, LEASE_DURATION, lease_token)
           
           if not job:
               print(f"Job {ready_job_id} is currently being processed by another worker.")
               time.sleep(1)    
               continue
           
           
           
           popped_job_id = queue.pop_job(ready_job_id)
           if not popped_job_id:
               print(f"Job {ready_job_id} was already claimed by another worker.")
               time.sleep(1)    
               continue
           hb_thread.start()
           try:
               result = dispatcher.execute_job(job)
               print(result)
               
               success = repo.complete_job(session, job.id, worker_id, job.lease_token)
               if not success:
                   print("Lost lease, skipping completion")
           except Exception as e:
               if job.attempts < job.max_retries:
                   retry_result = job_service.retry_job(session, job.id)
                   if retry_result:
                       queue.enqueue(job.id, retry_result["available_at"].timestamp())
                    
                   else:
                       repo.mark_job_as_failed(session, job_id=job.id, worker_id=worker_id, lease_token=job.lease_token)
           finally:
               stop_event.set()
               hb_thread.join()
                     
            

           
run_worker()       