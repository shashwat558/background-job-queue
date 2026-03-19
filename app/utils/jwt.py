from jose import jwt
from datetime import datetime, timedelta
from app.core.config import SECRET_KEY

def create_jwt(user_id):
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(hours=48)
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def decode_jwt(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except jwt.JWTError:
        return None
