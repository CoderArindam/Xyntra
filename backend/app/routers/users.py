import logging
from typing import List
from fastapi import APIRouter, Depends, Request, UploadFile, File
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.schemas.auth import UserResponse
from app.schemas.common import DataEnvelope
from app.schemas.users import UserUpdate, ChangePassword
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

def get_user_service(conn = Depends(get_db_connection)) -> UserService:
    return UserService(conn)

@router.get("", response_model=DataEnvelope[List[UserResponse]])
async def get_all_users(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Returns all users scoped to the caller's organization."""
    users = await user_service.get_all_users(current_user)
    return DataEnvelope(data=users)


@router.patch("/me", response_model=DataEnvelope[UserResponse])
async def update_me(
    payload: UserUpdate,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.update_me(payload, current_user)
    return DataEnvelope(data=user)


@router.put("/me/password", status_code=204)
async def change_password(
    payload: ChangePassword,
    request: Request,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    ip_address = request.client.host if request.client else "Unknown"
    await user_service.change_password(payload, current_user, ip_address)
    return None


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    url = await user_service.upload_avatar(file, current_user)
    return DataEnvelope(data={"avatar_url": url})


@router.delete("/me/avatar", status_code=204)
async def delete_avatar(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    await user_service.delete_avatar(current_user)
    return None
