from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.services import NameOfServices, Service
from app.models.user import User
from app.api.deps import get_current_user


router = APIRouter()


class UpdateMeRequest(BaseModel):
	avatar_url: str | None = None


class AddServiceRequest(BaseModel):
	name: NameOfServices
	api_key: str


def _get_user_or_404(user_id: uuid.UUID, session: Session) -> User:
	user = session.get(User, user_id)
	if not user:
		raise HTTPException(status_code=404, detail="User not found")
	return user


@router.get("/me")
def get_me(current_user: str = Depends(get_current_user), session: Session = Depends(get_session)):
	user_id = uuid.UUID(current_user)
	user = _get_user_or_404(user_id, session)
	return {
		"id": str(user.id),
		"email": user.email,
		"avatar_url": user.avatar_url,
		"is_active": user.is_active,
		"is_verified": user.is_verified,
		"provider": user.provider,
		"created_at": user.created_at,
		"updated_at": user.updated_at,
	}


@router.patch("/me")
def update_me(
	payload: UpdateMeRequest,
	current_user: str = Depends(get_current_user),
	session: Session = Depends(get_session),
):
	user_id = uuid.UUID(current_user)
	user = _get_user_or_404(user_id, session)

	if payload.avatar_url is not None:
		user.avatar_url = payload.avatar_url

	user.updated_at = datetime.utcnow()
	session.add(user)
	session.commit()
	session.refresh(user)

	return {
		"id": str(user.id),
		"email": user.email,
		"avatar_url": user.avatar_url,
		"updated_at": user.updated_at,
	}


@router.delete("/me")
def deactivate_me(current_user: str = Depends(get_current_user), session: Session = Depends(get_session)):
	user_id = uuid.UUID(current_user)
	user = _get_user_or_404(user_id, session)

	user.is_active = False
	user.updated_at = datetime.utcnow()
	session.add(user)
	session.commit()

	return {"success": True, "message": "User deactivated"}


@router.get("/me/services")
def get_my_services(current_user: str = Depends(get_current_user), session: Session = Depends(get_session)):
	user_id = uuid.UUID(current_user)
	_get_user_or_404(user_id, session)
	statement = select(Service).where(Service.user_id == user_id)
	services = session.exec(statement).all()
	return services


@router.post("/me/services")
def add_my_service(
	payload: AddServiceRequest,
	current_user: str = Depends(get_current_user),
	session: Session = Depends(get_session),
):
	user_id = uuid.UUID(current_user)
	_get_user_or_404(user_id, session)

	service = Service(
		user_id=user_id,
		name=payload.name,
		api_key=payload.api_key,
	)
	session.add(service)
	session.commit()
	session.refresh(service)
	return service


@router.delete("/me/services/{service_id}")
def delete_my_service(
	service_id: uuid.UUID,
	current_user: str = Depends(get_current_user),
	session: Session = Depends(get_session),
):
	user_id = uuid.UUID(current_user)
	_get_user_or_404(user_id, session)

	statement = select(Service).where(
		Service.id == service_id,
		Service.user_id == user_id,
	)
	service = session.exec(statement).first()
	if not service:
		raise HTTPException(status_code=404, detail="Service not found")

	session.delete(service)
	session.commit()
	return {"success": True, "message": "Service removed"}


@router.get("/{user_id}")
def get_user_public(user_id: uuid.UUID, session: Session = Depends(get_session)):
	user = _get_user_or_404(user_id, session)
	return {
		"id": str(user.id),
		"email": user.email,
		"avatar_url": user.avatar_url,
		"is_verified": user.is_verified,
		"created_at": user.created_at,
	}