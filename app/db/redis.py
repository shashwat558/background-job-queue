import redis
from app.core.config import REDIS_HOST_URL, REDIS_PASSWORD 
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
    db=0
)
