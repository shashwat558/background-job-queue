"""
Stale Lease Reaper — background watchdog that rescues orphaned jobs.

A job becomes "stale" when a worker crashes mid-execution and the lease
expires without being renewed.  This reaper periodically scans for such
jobs and either requeues them (if retries remain) or marks them failed.

Run as a daemon thread inside the worker process, or as a standalone process.
"""

import time
import logging
from sqlmodel import Session
from app.db.session import engine
from app.repository.job_repository import JobRepository
from app.queue.job_queue import JobQueue

logger = logging.getLogger(__name__)

# How often the reaper wakes up (seconds)
REAPER_INTERVAL = 30


def run_reaper():
    repo = JobRepository()
    queue = JobQueue()

    logger.info("Stale lease reaper started (interval=%ss)", REAPER_INTERVAL)

    while True:
        try:
            _sweep(repo, queue)
        except Exception:
            logger.exception("Reaper sweep error — will retry next cycle")

        time.sleep(REAPER_INTERVAL)


def _sweep(repo: JobRepository, queue: JobQueue):
    with Session(engine) as session:
        stale_jobs = repo.get_stale_running_jobs(session)

        if not stale_jobs:
            logger.debug("reaper.sweep: no stale jobs found")
            return

        logger.warning("reaper.sweep: found %d stale job(s)", len(stale_jobs))

        for job in stale_jobs:
            if job.attempts < job.max_retries:
                repo.requeue_stale_job(session, job)
                priority = (
                    job.priority.value
                    if hasattr(job.priority, "value")
                    else str(job.priority)
                )
                queue.enqueue(job.id, job.available_at or _now_datetime(), priority)
                logger.warning(
                    "reaper: requeued stale job id=%s attempts=%s/%s",
                    job.id, job.attempts, job.max_retries,
                )
            else:
                repo.mark_stale_job_failed(session, job)
                queue.send_to_dlq(job.id)
                logger.error(
                    "reaper: permanently failed stale job id=%s (max retries=%s)",
                    job.id, job.max_retries,
                )


def _now_datetime():
    from datetime import datetime
    return datetime.now()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    run_reaper()
