from app.workers.tasks.send_email import send_email
from app.workers.tasks.generate_report import generate_report
from app.models.job import Job
TASK_REGISTRY = {
    "email": send_email,
    "generate_report": generate_report 
}

class Dispatcher:
    def execute_job(job:Job):
        task = TASK_REGISTRY.get(job.type)
        
        if not task:
            raise Exception("Unknown job type")
        
        response = task(job.payload)
        if response["status"] == "success":
            return True
        
        return False
            
        
        
        
        