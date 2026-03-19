from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import job_routes
from app.api.v1 import user_route
from app.api.v1 import auth_routes
app = FastAPI(title="job-queue-system")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials= True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(job_routes.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(user_route.router, prefix="/api/v1/users", tags=["users"])
app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["auth"])

@app.get("/")
def root():
    return {"status": "ok", "message": "backend running"}

@app.get("/health")
def health():
    return {"status": "healthy"}


