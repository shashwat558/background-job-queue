from fastapi import APIRouter, Depends
from app.schemas.auth import LoginRequest, SignupRequest
from app.db.session import get_session
from sqlmodel import Session 
from app.services.auth_service import signup_user, login_user, google_auth_login
from app.utils.google_auth import verify_google_token
from app.core.config import GOOGLE_CLIENT_ID
router = APIRouter()



@router.post("/signup")
def signup(data:SignupRequest, session:Session = Depends(get_session)):
    token = signup_user(data.email, data.password, session)
    return {"token": token}

@router.post("/login")
def login(data:LoginRequest, session:Session = Depends(get_session)):
    token = login_user(data.email, data.password, session=session)
    return {"token": token}

@router.post("/google")
def google_login(token:str, session:Session = Depends(get_session)):
    idinfo = verify_google_token(token, client_id=GOOGLE_CLIENT_ID)
    email = idinfo["email"]
    google_id = idinfo["sub"]
    avatar_url = idinfo.get("pictur")
    
    token = google_auth_login(email=email, google_id=google_id, avatar_url=avatar_url, session=session)
    return {"token": token}