import os
from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

SECRET_KEY = os.getenv("SECRET_KEY", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
REDIS_HOST_URL = os.getenv("REDIS_HOST_URL", "redis://localhost:6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# CORS — set a comma-separated list in ALLOWED_ORIGINS env var for production.
# Example:  ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins
    else ["*"]   # dev fallback only
)

# Email connection — only initialised when SMTP credentials are present so
# that workers that never send email don't crash on import.
conf: ConnectionConfig | None = None
if SMTP_EMAIL and SMTP_PASSWORD:
    conf = ConnectionConfig(
        MAIL_USERNAME=SMTP_EMAIL,
        MAIL_PASSWORD=SMTP_PASSWORD,
        MAIL_FROM=SMTP_EMAIL,
        MAIL_PORT=587,
        MAIL_SERVER="smtp.gmail.com",
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
    )

# ── Worker tunables ────────────────────────────────────────────────────────────
LEASE_DURATION: int = int(os.getenv("LEASE_DURATION", "30"))
HEARTBEAT_INTERVAL: int = int(os.getenv("HEARTBEAT_INTERVAL", "10"))

# Threads per worker process (default 2; tune via env var)
WORKER_CONCURRENCY: int = int(os.getenv("WORKER_CONCURRENCY", "2"))