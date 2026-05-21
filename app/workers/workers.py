"""
Worker pool — runs N concurrent workers + the stale-lease reaper.

Each worker:
  1. Atomically claims a ready job from Redis (Lua script, no race condition).
  2. Claims the job in Postgres with lease/token ownership.
  3. Runs a background heartbeat thread to renew the lease.
  4. Executes the job via the Dispatcher.
  5. Marks it complete or schedules a retry on failure.

Scalability levers
------------------
  WORKER_CONCURRENCY  — parallel workers in this process (default: CPU count)
  LEASE_DURATION      — seconds a lease lives without a heartbeat
  HEARTBEAT_INTERVAL  — how often the heartbeat fires

Run multiple OS processes of this script to scale across machines.
"""

import os
import time
import uuid
import signal
import socket
import logging
import threading
import multiprocessing
from datetime import datetime

from sqlmodel import Session

from app.db.session import engine
from app.queue.job_queue import JobQueue
from app.repository.job_repository import JobRepository
from app.workers.dispatcher import Dispatcher
from app.services.job_services import JobService
from app.workers.reaper import run_reaper
from app.core.config import LEASE_DURATION, HEARTBEAT_INTERVAL, WORKER_CONCURRENCY

logger = logging.getLogger(__name__)

# ── Graceful shutdown ─────────────────────────────────────────────────────────
_shutdown = threading.Event()

def _handle_signal(signum, frame):
    logger.info("Received signal %s — shutting down workers gracefully…", signum)
    _shutdown.set()

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# ── ID helpers ────────────────────────────────────────────────────────────────

def _make_worker_id() -> str:
    return f"{socket.gethostname()}_{os.getpid()}_{uuid.uuid4().hex[:8]}"


def _make_lease_token() -> str:
    return uuid.uuid4().hex


# ── Heartbeat ─────────────────────────────────────────────────────────────────

def _heartbeat_loop(
    repo: JobRepository,
    job_id: int,
    worker_id: str,
    lease_token: str,
    stop_event: threading.Event,
):
    """Runs in a daemon thread; renews the lease every HEARTBEAT_INTERVAL seconds."""
    while not stop_event.is_set():
        stop_event.wait(timeout=HEARTBEAT_INTERVAL)
        if stop_event.is_set():
            break
        try:
            with Session(engine) as session:
                ok = repo.renew_lease(
                    session, job_id, worker_id, lease_token, LEASE_DURATION
                )
            if not ok:
                logger.warning(
                    "worker=%s lost lease on job=%s — stopping heartbeat",
                    worker_id, job_id,
                )
                stop_event.set()
        except Exception:
            logger.exception("Heartbeat error for job=%s", job_id)


# ── Single worker loop ────────────────────────────────────────────────────────

def _run_single_worker(worker_id: str):
    repo = JobRepository()
    queue = JobQueue()
    dispatcher = Dispatcher()
    job_service = JobService(repo=repo, queue=queue)

    logger.info("Worker %s started", worker_id)

    while not _shutdown.is_set():
        # ── 1. Atomic claim from Redis ─────────────────────────────────────
        job_id_str = queue.atomic_claim_ready_job(now=time.time())
        if job_id_str is None:
            _shutdown.wait(timeout=1)   # sleep 1s, but wake immediately on shutdown
            continue

        lease_token = _make_lease_token()

        # ── 2. Claim in Postgres ───────────────────────────────────────────
        with Session(engine) as session:
            job = repo.try_claim_job(
                session, job_id_str, worker_id, LEASE_DURATION, lease_token
            )

            if not job:
                logger.debug(
                    "worker=%s: job %s already claimed by another worker",
                    worker_id, job_id_str,
                )
                continue

            claimed_id = job.id
            claimed_token = job.lease_token

            # ── 3. Start heartbeat ─────────────────────────────────────────
            stop_event = threading.Event()
            hb_thread = threading.Thread(
                target=_heartbeat_loop,
                args=(repo, claimed_id, worker_id, claimed_token, stop_event),
                daemon=True,
                name=f"hb-{claimed_id}",
            )
            hb_thread.start()

            # ── 4. Execute ─────────────────────────────────────────────────
            try:
                result = dispatcher.execute_job(job)
                logger.info(
                    "worker=%s job=%s completed result=%s", worker_id, claimed_id, result
                )
                repo.complete_job(session, claimed_id, worker_id, claimed_token)

            except Exception as exc:
                logger.error(
                    "worker=%s job=%s failed: %s", worker_id, claimed_id, exc, exc_info=True
                )
                retry_info = job_service.retry_job(session, claimed_id)
                if retry_info and retry_info.get("available_at"):
                    queue.enqueue(
                        retry_info["job_id"],
                        retry_info["available_at"],
                        retry_info.get("priority", "low"),
                    )
                    logger.info(
                        "worker=%s job=%s scheduled for retry at %s",
                        worker_id, claimed_id, retry_info["available_at"],
                    )
                else:
                    # No retries left — mark failed and send to DLQ
                    repo.mark_job_as_failed(
                        session, claimed_id, worker_id, claimed_token
                    )
                    queue.send_to_dlq(claimed_id)
                    logger.error(
                        "worker=%s job=%s sent to dead-letter queue", worker_id, claimed_id
                    )

            finally:
                stop_event.set()
                hb_thread.join(timeout=5)

    logger.info("Worker %s exiting cleanly", worker_id)


# ── Worker process entry point (used by multiprocessing) ─────────────────────

def _worker_process_main(concurrency: int):
    """Entry point for each OS process. Spawns `concurrency` threads."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s/%(threadName)s] %(message)s",
    )

    threads = []
    for _ in range(concurrency):
        worker_id = _make_worker_id()
        t = threading.Thread(
            target=_run_single_worker,
            args=(worker_id,),
            name=worker_id,
            daemon=False,
        )
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


# ── Main: spawn worker processes + reaper ─────────────────────────────────────

def run_worker_pool(
    num_processes: int | None = None,
    concurrency_per_process: int = WORKER_CONCURRENCY,
):
    """
    Spawn `num_processes` OS processes, each running `concurrency_per_process`
    worker threads, plus one reaper daemon thread in this process.

    Default: 1 process per logical CPU, 2 workers per process.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s/%(threadName)s] %(message)s",
    )

    if num_processes is None:
        num_processes = max(1, os.cpu_count() or 1)

    # ── Start stale-lease reaper in a background daemon thread ────────────
    reaper_thread = threading.Thread(
        target=run_reaper,
        name="stale-lease-reaper",
        daemon=True,
    )
    reaper_thread.start()
    logger.info("Reaper daemon thread started")

    # ── Spawn worker processes ─────────────────────────────────────────────
    processes: list[multiprocessing.Process] = []
    for _ in range(num_processes):
        p = multiprocessing.Process(
            target=_worker_process_main,
            args=(concurrency_per_process,),
            daemon=False,
        )
        p.start()
        processes.append(p)

    logger.info(
        "Worker pool started: %d process(es) × %d thread(s) = %d total workers",
        num_processes, concurrency_per_process, num_processes * concurrency_per_process,
    )

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt — signalling workers to stop")
        _shutdown.set()
        for p in processes:
            p.join(timeout=30)
            if p.is_alive():
                p.terminate()


if __name__ == "__main__":
    run_worker_pool()