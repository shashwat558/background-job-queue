from fastapi import HTTPException, Request
from app.utils.jwt import decode_jwt

def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Strip "Bearer " prefix if present
    token = auth_header.removeprefix("Bearer ").strip()

    user_id = decode_jwt(token=token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_id