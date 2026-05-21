from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import QueuePool
from app.core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    echo=False,                 # disable in prod — was spamming stdout
    poolclass=QueuePool,
    pool_size=20,               # max persistent connections
    max_overflow=40,            # extra connections under spike load
    pool_timeout=30,            # wait up to 30s for a free connection
    pool_pre_ping=True,         # validate connection health before use
    pool_recycle=1800,          # recycle connections every 30 min
)

def get_session():
    with Session(engine) as session:
        yield session