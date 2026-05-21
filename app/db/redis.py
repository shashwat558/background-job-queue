import redis
from app.core.config import REDIS_HOST_URL, REDIS_PASSWORD

# Connection pool: shared across all threads/workers in this process.
# max_connections caps total sockets; each thread borrows from the pool.
_pool = redis.ConnectionPool.from_url(
    REDIS_HOST_URL,
    password=REDIS_PASSWORD,
    decode_responses=True,
    max_connections=50,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
    health_check_interval=30,
)

redis_client = redis.Redis(connection_pool=_pool)
