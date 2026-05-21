"""
Job routes — CRUD + status + listing for the authenticated user's jobs.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.job import Job, JobStatus
from app.queue.job_queue import JobQueue
from app.repository.job_repository import JobRepository
from app.schemas.job import JobCreateRequest, JobResponse
from app.services.job_services import JobService

router = APIRouter()

# ── shared dependencies ────────────────────────────────────────────────────────

def _get_service(session: Session = Depends(get_session)) -> JobService:
    return JobService(repo=JobRepository(), queue=JobQueue())


# ── endpoints ──────────────────────────────────────────────────────────────────

@router.post("/", response_model=JobResponse, status_code=201)
def create_job(
    data: Annotated[JobCreateRequest, Body()],
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Create and enqueue a new job."""
    service = JobService(repo=JobRepository(), queue=JobQueue())
    available_at = data.scheduled_at or datetime.now()
    job = Job(
        type=data.type,
        priority=data.priority,
        scheduled_at=data.scheduled_at,
        available_at=available_at,
        user_id=uuid.UUID(current_user),
        payload=data.payload.model_dump(),
    )
    return service.create_job(session=session, job_data=job)


@router.get("/", response_model=list[JobResponse])
def list_jobs(
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session),
    status: str | None = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List the current user's jobs with optional status filter and pagination."""
    repo = JobRepository()
    return repo.get_jobs_for_user(
        session,
        user_id=uuid.UUID(current_user),
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/queue/stats")
def queue_stats():
    """Real-time queue depth metrics (no auth required — safe to expose internally)."""
    import time
    q = JobQueue()
    return {
        "total_queued": q.depth(),
        "ready_now": q.ready_depth(now=time.time()),
        "dead_letter": q.dlq_depth(),
    }


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Fetch a single job. Returns 404 if not found or not owned by caller."""
    repo = JobRepository()
    job = repo.get_job(session, job_id)
    if not job or str(job.user_id) != current_user:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/{job_id}", status_code=204)
def cancel_job(
    job_id: int,
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Cancel a queued job.  Only jobs in 'queued' or 'retry_scheduled' state
    can be cancelled — running jobs cannot be interrupted.
    """
    repo = JobRepository()
    job = repo.get_job(session, job_id)
    if not job or str(job.user_id) != current_user:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ("queued", "retry_scheduled"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel a job in '{job.status}' state",
        )

    # Remove from Redis queue, mark cancelled in DB
    queue = JobQueue()
    queue.pop_job(job_id)
    job.status = JobStatus.CANCELLED
    session.add(job)
    session.commit()
    return
