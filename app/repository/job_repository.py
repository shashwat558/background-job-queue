"""
JobRepository — all DB operations for the Job model.

Design rules:
- Every method owns its commit; callers must NOT commit after calling these.
- Lease ownership is always triple-verified: worker_id + lease_token + status.
- datetime.now() (no tz) is used everywhere for consistency with SQLite/PG TIMESTAMP WITHOUT TIME ZONE.
"""

from sqlmodel import Session, select
from app.models.job import Job, JobStatus
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class JobRepository:

    # ─────────────────────────────────────────────────────────────────────
    # CRUD
    # ─────────────────────────────────────────────────────────────────────

    def create_job(self, session: Session, job_data: Job) -> Job:
        session.add(job_data)
        session.commit()
        session.refresh(job_data)
        logger.info("job.created id=%s type=%s", job_data.id, job_data.type)
        return job_data

    def get_job(self, session: Session, job_id) -> Job | None:
        return session.get(Job, job_id)

    def get_jobs_for_user(
        self,
        session: Session,
        user_id,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Job]:
        stmt = select(Job).where(Job.user_id == user_id)
        if status:
            stmt = stmt.where(Job.status == status)
        stmt = stmt.order_by(Job.created_at.desc()).offset(offset).limit(limit)
        return session.exec(stmt).all()

    # ─────────────────────────────────────────────────────────────────────
    # Worker lifecycle
    # ─────────────────────────────────────────────────────────────────────

    def try_claim_job(
        self,
        session: Session,
        job_id,
        worker_id: str,
        lease_duration: int,
        lease_token: str,
    ) -> Job | None:
        """
        Atomically claim a queued job.  Returns the Job on success, None otherwise.

        Note: attempts is NOT incremented here.  The retry/failure counter is
        incremented only in retry_job so we never double-count.
        """
        job: Job | None = session.get(Job, job_id)
        if job is None:
            return None

        claimable = (
            job.status in (JobStatus.QUEUED, JobStatus.RETRY_SCHEDULED)
            or (
                job.lease_expires_at is not None
                and job.lease_expires_at < datetime.now()
            )
        )
        if not claimable:
            return None

        now = datetime.now()
        job.status = JobStatus.RUNNING
        job.worker_id = worker_id
        job.lease_expires_at = now + timedelta(seconds=lease_duration)
        job.lease_token = lease_token
        job.last_heartbeat_at = now
        job.started_at = now
        session.add(job)
        session.commit()
        session.refresh(job)
        logger.info("job.claimed id=%s worker=%s", job.id, worker_id)
        return job

    def complete_job(
        self, session: Session, job_id, worker_id: str, lease_token: str
    ) -> int | None:
        job: Job | None = session.get(Job, job_id)
        if (
            job
            and job.worker_id == worker_id
            and job.lease_token == lease_token
            and job.status == JobStatus.RUNNING
        ):
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.lease_token = None
            job.worker_id = None
            job.lease_expires_at = None
            session.add(job)
            session.commit()
            logger.info("job.completed id=%s", job_id)
            return job.id
        logger.warning("job.complete_skipped id=%s (ownership mismatch)", job_id)
        return None

    def mark_job_as_failed(
        self, session: Session, job_id, worker_id: str, lease_token: str
    ) -> int | None:
        job: Job | None = session.get(Job, job_id)
        if (
            job
            and job.worker_id == worker_id
            and job.lease_token == lease_token
            and job.status == JobStatus.RUNNING
        ):
            job.status = JobStatus.FAILED
            job.failed_at = datetime.now()
            job.lease_token = None
            job.worker_id = None
            job.lease_expires_at = None
            session.add(job)
            session.commit()
            logger.warning("job.failed id=%s attempts=%s", job_id, job.attempts)
            return job.id
        return None

    def renew_lease(
        self,
        session: Session,
        job_id,
        worker_id: str,
        lease_token: str,
        lease_duration: int,
    ) -> bool:
        job: Job | None = session.get(Job, job_id)
        if (
            job
            and job.worker_id == worker_id
            and job.lease_token == lease_token
            and job.status == JobStatus.RUNNING
        ):
            now = datetime.now()
            job.last_heartbeat_at = now
            job.lease_expires_at = now + timedelta(seconds=lease_duration)
            session.add(job)
            session.commit()
            return True
        logger.warning("job.renew_lease_failed id=%s", job_id)
        return False

    # ─────────────────────────────────────────────────────────────────────
    # Stale lease reaper support
    # ─────────────────────────────────────────────────────────────────────

    def get_stale_running_jobs(self, session: Session) -> list[Job]:
        """Return jobs stuck in RUNNING with an expired lease."""
        stmt = select(Job).where(
            Job.status == JobStatus.RUNNING,
            Job.lease_expires_at < datetime.now(),
        )
        return session.exec(stmt).all()

    def requeue_stale_job(self, session: Session, job: Job) -> None:
        """Reset a stale job back to QUEUED so a worker can re-claim it."""
        job.status = JobStatus.QUEUED
        job.worker_id = None
        job.lease_token = None
        job.lease_expires_at = None
        job.last_heartbeat_at = None
        session.add(job)
        session.commit()
        logger.warning("job.requeued_stale id=%s", job.id)

    def mark_stale_job_failed(self, session: Session, job: Job) -> None:
        """Mark a stale job as failed (max retries exhausted)."""
        job.status = JobStatus.FAILED
        job.failed_at = datetime.now()
        job.worker_id = None
        job.lease_token = None
        job.lease_expires_at = None
        session.add(job)
        session.commit()
        logger.warning("job.stale_failed id=%s", job.id)