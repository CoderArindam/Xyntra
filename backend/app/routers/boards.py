import logging
import asyncpg
from typing import List
from fastapi import APIRouter, Depends, HTTPException

from app.schemas.board import BoardCreate, CanonicalBoardResponse, ProjectSettingsResponse, ProjectSettingsUpdate
from app.schemas.envelope import DataEnvelope
from app.auth.dependencies import get_current_user
from app.auth.permissions import require_manager_or_above
from app.database.connection import get_db_connection
from app.services.board_service import BoardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/boards", tags=["Boards"])

def get_board_service(conn: asyncpg.Connection = Depends(get_db_connection)) -> BoardService:
    return BoardService(conn)

@router.post("", response_model=DataEnvelope[CanonicalBoardResponse])
async def create_board(
    board_in: BoardCreate,
    current_user: dict = Depends(require_manager_or_above),
    board_service: BoardService = Depends(get_board_service)
):
    board = await board_service.create_board(board_in, current_user)
    return DataEnvelope(data=board)

@router.get("", response_model=DataEnvelope[List[CanonicalBoardResponse]])
async def get_user_boards(
    include_archived: bool = False,
    current_user: dict = Depends(get_current_user),
    board_service: BoardService = Depends(get_board_service)
):
    boards = await board_service.get_user_boards(include_archived, current_user)
    return DataEnvelope(data=boards)

@router.get("/{board_id}/settings", response_model=DataEnvelope[ProjectSettingsResponse])
async def get_project_settings(
    board_id: int,
    current_user: dict = Depends(get_current_user),
    board_service: BoardService = Depends(get_board_service)
):
    settings = await board_service.get_project_settings(board_id, current_user)
    return DataEnvelope(data=settings)

@router.patch("/{board_id}/settings", response_model=DataEnvelope[ProjectSettingsResponse])
async def update_project_settings(
    board_id: int,
    updates: ProjectSettingsUpdate,
    current_user: dict = Depends(get_current_user),
    board_service: BoardService = Depends(get_board_service)
):
    settings = await board_service.update_project_settings(board_id, updates, current_user)
    return DataEnvelope(data=settings)

@router.post("/{board_id}/archive", response_model=DataEnvelope[ProjectSettingsResponse])
async def archive_project(
    board_id: int,
    current_user: dict = Depends(get_current_user),
    board_service: BoardService = Depends(get_board_service)
):
    settings = await board_service.archive_project(board_id, current_user)
    return DataEnvelope(data=settings)

@router.delete("/{board_id}", status_code=204)
async def delete_board(
    board_id: int,
    current_user: dict = Depends(get_current_user),
    board_service: BoardService = Depends(get_board_service)
):
    await board_service.delete_board(board_id, current_user)
    return None
