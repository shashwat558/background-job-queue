from app.db.redis import redis_client
from datetime import datetime, timezone
class JobQueue:
    
    def enqueue(self, job_id, timestamp):
        if isinstance(timestamp, datetime):
            dt = timestamp
        else: 
           dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        if dt.tzinfo is None:            
            dt = dt.replace(tzinfo=timezone.utc)
        timestamp_to_int = int(dt.timestamp())
        redis_client.zadd("job_queue", {job_id:timestamp_to_int})
    
    def pop_ready_job(self, now):
    
        all_jobs = redis_client.zrange("job_queue", 0, -1, withscores=True)
        print(f"[DEBUG] Current time: {now}")
        print(f"[DEBUG] Jobs in queue: {all_jobs}")
        
        ready_jobs = redis_client.zrangebyscore("job_queue", 0, now, start=0, num=1)
        print(f"[DEBUG] Ready jobs: {ready_jobs}")
        
        if not ready_jobs:
            return None
        
        job_id = ready_jobs[0]
        redis_client.zrem("job_queue", job_id)
        return job_id
    