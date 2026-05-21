"""
JobService — business logic layer sitting above the repository.

Retry logic:
- attempts is incremented here (not in the repository) to avoid double-counting.
- The guard  job.attempts < job.max_retries  is checked BEFORE incrementing,
  so a job with max_retries=3 will get exactly 3 execution attempts total.
"""

from sqlmodel import Session
from app.models.job import Job
from app.utils.job_utils import exponential_backoff
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class JobService:
    def __init__(self, repo, queue):
        self.repo = repo
        self.queue = queue

    def create_job(self, session: Session, job_data: Job) -> Job:
        job = self.repo.create_job(session, job_data)
        priority = job.priority.value if hasattr(job.priority, "value") else str(job.priority)
        self.queue.enqueue(job.id, job_data.available_at, priority=priority)
        return job

    def retry_job(self, session: Session, job_id: str) -> dict | None:
        """
        Schedule a retry for a failed job.

        Returns {"job_id": ..., "available_at": ...} on success, None if the
        job doesn't exist or has already exhausted its retries.
        """
        job: Job | None = self.repo.get_job(session, job_id)

        if job is None:
            logger.warning("retry_job: job %s not found", job_id)
            return None

        # Guard: check BEFORE incrementing — so max_retries=3 means 3 total runs
        if job.attempts >= job.max_retries:
            logger.warning(
                "retry_job: job %s exhausted retries (attempts=%s max=%s)",
                job_id, job.attempts, job.max_retries,
            )
            return None

        # Increment attempt counter
        job.attempts += 1

        base_time = job.available_at if job.available_at is not None else datetime.now()
        job.available_at = base_time + timedelta(seconds=exponential_backoff(job.attempts))
        job.status = "retry_scheduled"
        job.worker_id = None
        job.lease_expires_at = None
        job.lease_token = None
        job.last_heartbeat_at = None
        job.started_at = None

        session.add(job)
        session.commit()
        session.refresh(job)

        logger.info(
            "job.retry_scheduled id=%s attempt=%s/%s available_at=%s",
            job.id, job.attempts, job.max_retries, job.available_at,
        )

        priority = job.priority.value if hasattr(job.priority, "value") else str(job.priority)
        return {
            "job_id": job.id,
            "available_at": job.available_at,
            "priority": priority,
        }