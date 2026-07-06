import logging
from typing import List
from fastapi import APIRouter, Depends, status

from app.schemas.admin import UserCreateAdmin, UserRoleUpdate, AdminUserResponse, AdminBoardResponse, BoardMemberAssign, AdminBoardMemberResponse
from app.auth.permissions import require_super_admin
from app.database.connection import get_db_connection
from app.services.admin_service import AdminService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


def get_admin_service(conn = Depends(get_db_connection)) -> AdminService:
    return AdminService(conn)

@router.get("/users", response_model=List[AdminUserResponse])
async def get_all_users(
    current_user: dict = Depends(require_super_admin),
    admin_service: AdminService = Depends(get_admin_service)
):
    return await admin_service.get_all_users(current_user)

@router.post("/users", response_model=AdminUserResponse)
async def create_user(
    user_in: UserCreateAdmin,
    current_user: dict = Depends(require_super_admin),
    admin_service: AdminService = Depends(get_admin_service)
):
    return await admin_service.create_user(user_in, current_user)

@router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
async def update_user_role(
    user_id: int,
    role_in: UserRoleUpdate,
    current_user: dict = Depends(require_super_admin),
    admin_service: AdminService = Depends(get_admin_service)
):
    return await admin_service.update_user_role(user_id, role_in, current_user)

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: dict = Depends(require_super_admin),
    admin_service: AdminService = Depends(get_admin_service)
):
    await admin_service.delete_user(user_id, current_user)
    return None

@router.get("/boards", response_model=List[AdminBoardResponse])
async def get_all_boards(
    current_user: dict = Depends(require_super_admin),
    admin_service: AdminService = Depends(get_admin_service)
):
    return await admin_service.get_all_boards(current_user)

@router.post("/boards/{board_id}/members", status_code=status.HTTP_201_CREATED)
async def assign_user(
    board_id: int,
    assign_in: BoardMemberAssign,
    current_user: dict = Depends(require_super_admin),
    admin_service: AdminService = Depends(get_admin_service)
):
    await admin_service.assign_user(board_id, assign_in, current_user)
    return {"message": "User assigned to board"}

@router.delete("/boards/{board_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    board_id: int,
    user_id: int,
    current_user: dict = Depends(require_super_admin),
    admin_service: AdminService = Depends(get_admin_service)
):
    await admin_service.remove_user(board_id, user_id)
    return None

@router.get("/boards/{board_id}/members", response_model=List[AdminBoardMemberResponse])
async def get_board_members_admin(
    board_id: int,
    current_user: dict = Depends(require_super_admin),
    admin_service: AdminService = Depends(get_admin_service)
):
    return await admin_service.get_board_members_admin(board_id)
