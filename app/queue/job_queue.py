"""
JobQueue — Redis-backed sorted-set queue with priority support.

Score formula:
    score = available_at_unix  -  (priority_weight * PRIORITY_BOOST)

Lower score = runs sooner.  HIGH priority jobs are pulled before LOW ones
even if they arrive at the same wall-clock second.
"""

from app.db.redis import redis_client
from datetime import datetime, timezone

QUEUE_KEY = "job_queue"
DLQ_KEY = "job_dead_letter"     # jobs that exhausted all retries

# Priority boost subtracts from the UNIX timestamp so high-priority jobs
# sort ahead of low-priority ones that have the same available_at.
PRIORITY_WEIGHT = {
    "high":   1_000,
    "medium": 500,
    "low":    0,
}

# Lua script: atomic peek-then-remove in a single round-trip.
# Returns the job_id string if a ready job existed, nil otherwise.
_CLAIM_SCRIPT = redis_client.register_script("""
local key   = KEYS[1]
local now   = tonumber(ARGV[1])
local items = redis.call('ZRANGEBYSCORE', key, '-inf', now, 'LIMIT', 0, 1)
if #items == 0 then return nil end
local job_id = items[1]
redis.call('ZREM', key, job_id)
return job_id
""")


class JobQueue:

    def enqueue(self, job_id: str | int, available_at, priority: str = "low"):
        """Push a job onto the sorted set with a priority-adjusted score."""
        if isinstance(available_at, datetime):
            dt = available_at
        else:
            dt = datetime.strptime(str(available_at), "%Y-%m-%d %H:%M:%S")

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        score = int(dt.timestamp()) - PRIORITY_WEIGHT.get(priority, 0)
        redis_client.zadd(QUEUE_KEY, {str(job_id): score})

    def atomic_claim_ready_job(self, now: float) -> str | None:
        """
        Atomically peek *and* remove one ready job using a Lua script.
        Eliminates the TOCTOU race between get_ready_job_id + pop_job.
        Returns the job_id string or None.
        """
        result = _CLAIM_SCRIPT(keys=[QUEUE_KEY], args=[int(now)])
        return result  # None if queue empty

    # ── kept for backwards-compat with any external callers ──────────────
    def get_ready_job_id(self, now: float) -> str | None:
        ready = redis_client.zrangebyscore(QUEUE_KEY, 0, int(now), start=0, num=1)
        return ready[0] if ready else None

    def pop_job(self, job_id: str | int) -> int:
        return redis_client.zrem(QUEUE_KEY, str(job_id))

    # ── queue depth helpers ───────────────────────────────────────────────
    def depth(self) -> int:
        return redis_client.zcard(QUEUE_KEY)

    def ready_depth(self, now: float) -> int:
        return redis_client.zcount(QUEUE_KEY, 0, int(now))

    # ── dead-letter queue ─────────────────────────────────────────────────
    def send_to_dlq(self, job_id: str | int):
        """Move a permanently-failed job to the dead-letter sorted set."""
        import time
        redis_client.zadd(DLQ_KEY, {str(job_id): int(time.time())})

    def dlq_depth(self) -> int:
        return redis_client.zcard(DLQ_KEY)