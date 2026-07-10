from app.database.connection import get_db_connection
from fastapi import APIRouter, Depends
from typing import List
from app.auth.dependencies import get_current_user
from app.schemas.envelope import DataEnvelope
from app.services.board_service import BoardService

router = APIRouter(tags=["Board Members"])


def get_board_service(conn = Depends(get_db_connection)) -> BoardService:
    return BoardService(conn)

@router.get("/boards/{board_id}/members")
async def get_board_members(
    board_id: int,
    current_user: dict = Depends(get_current_user),
    board_service: BoardService = Depends(get_board_service),
):
    members = await board_service.get_board_members(board_id, current_user)
    return DataEnvelope(data=members)
