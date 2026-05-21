import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import auth_routes, job_routes, user_route
from app.core.config import ALLOWED_ORIGINS

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Job Queue System",
    version="2.0.0",
    description="Distributed background job queue with priority, lease-based locking, and retry.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# If ALLOWED_ORIGINS is ["*"] (dev default) we must NOT pass allow_credentials=True
# because browsers reject that combination per the CORS spec.
_wildcard = ALLOWED_ORIGINS == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=not _wildcard,   # only True when explicit origins are set
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(job_routes.router,  prefix="/api/v1/jobs",  tags=["jobs"])
app.include_router(user_route.router,  prefix="/api/v1/users", tags=["users"])
app.include_router(auth_routes.router, prefix="/api/v1/auth",  tags=["auth"])

# ── Health / root ──────────────────────────────────────────────────────────────
@app.get("/", tags=["meta"])
def root():
    return {"status": "ok", "message": "job-queue-system v2"}


@app.get("/health", tags=["meta"])
def health():
    """
    Liveness probe.  Add DB/Redis connectivity checks here if needed.
    """
    return {"status": "healthy"}
