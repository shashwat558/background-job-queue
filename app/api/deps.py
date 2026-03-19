from fastapi import HTTPException, Request
from app.utils.jwt import decode_jwt

def get_current_user(request: Request):
    token = request.headers.get("Authorization")
    
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = decode_jwt(token=token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid code")
    return user_id