from sqlmodel import select
from fastapi import HTTPException
from app.models.user import User
from app.db.session import Session
from app.utils.password import verify_password, hash_password
from app.utils.jwt import create_jwt


def login_user(email: str, password: str, session: Session) -> str:
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.hashed_password:
        raise HTTPException(status_code=400, detail="Account uses Google login — no password set")

    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password")

    return create_jwt(user_id=user.id)


def signup_user(email: str, password: str, session: Session):
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()

    if user:
        raise HTTPException(status_code=409, detail="User already exists")

    hashed_password = hash_password(password)
    user = User(
        email=email,
        hashed_password=hashed_password,
        provider="credentials",
        is_active=True,
        is_verified=False,
        google_id=None,
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "user_id": str(user.id),
        "token": create_jwt(user_id=user.id),
    }


def google_auth_login(email: str, google_id: str, avatar_url, session: Session):
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()

    if not user:
        user = User(
            email=email,
            google_id=google_id,
            avatar_url=avatar_url,
            is_verified=True,
            is_active=True,
            provider="google",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    jwt_token = create_jwt(user.id)
    return {"token": jwt_token}