import asyncio
from app.workers.tasks.send_email import send_email
from app.workers.tasks.generate_report import generate_report
from app.models.job import Job
from app.schemas.job import EmailPayload

TASK_REGISTRY = {
    "email": send_email,
    "generate_report": generate_report,
}

# Map job types to their payload schemas for deserialization
PAYLOAD_SCHEMAS = {
    "email": EmailPayload,
}

class Dispatcher:
    def execute_job(self, job: Job):
        task = TASK_REGISTRY.get(job.type)

        if not task:
            raise Exception(f"Unknown job type: {job.type!r}")

        # Deserialize raw dict payload into typed Pydantic model if schema exists
        schema = PAYLOAD_SCHEMAS.get(job.type)
        payload = schema(**job.payload) if schema else job.payload

        # Handle both sync and async task functions uniformly
        if asyncio.iscoroutinefunction(task):
            response = asyncio.run(task(payload))
        else:
            response = task(payload)

        if response.get("status") == "success":
            return True
        return False