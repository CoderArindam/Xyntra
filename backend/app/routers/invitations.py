import logging
from typing import List
from fastapi import APIRouter, Depends, BackgroundTasks, status

from app.schemas.invitations import (
    InviteUserRequest,
    InvitationResponse,
    AcceptInvitationRequest,
    InvitationDetailResponse,
)
from app.auth.permissions import require_manager_or_above
from app.database.connection import get_db_connection
from app.services.invitation_service import InvitationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invitations", tags=["Invitations"])


def get_invitation_service(conn = Depends(get_db_connection)) -> InvitationService:
    return InvitationService(conn)

@router.post("", response_model=InvitationResponse, status_code=201)
async def invite_user(
    invite_in: InviteUserRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_manager_or_above),
    invitation_service: InvitationService = Depends(get_invitation_service)
):
    invitation, email, org_name, token = await invitation_service.invite_user(invite_in, current_user)
    
    background_tasks.add_task(
        invitation_service._send_invitation_email, email, org_name, token
    )
    
    return invitation

@router.get("", response_model=List[InvitationResponse])
async def list_invitations(
    current_user: dict = Depends(require_manager_or_above),
    invitation_service: InvitationService = Depends(get_invitation_service)
):
    return await invitation_service.list_invitations(current_user)

@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: int,
    current_user: dict = Depends(require_manager_or_above),
    invitation_service: InvitationService = Depends(get_invitation_service)
):
    await invitation_service.revoke_invitation(invitation_id, current_user)
    return None

@router.get("/verify/{token}", response_model=InvitationDetailResponse)
async def verify_invitation(
    token: str,
    invitation_service: InvitationService = Depends(get_invitation_service)
):
    return await invitation_service.verify_invitation(token)

@router.post("/accept")
async def accept_invitation(
    body: AcceptInvitationRequest,
    invitation_service: InvitationService = Depends(get_invitation_service)
):
    await invitation_service.accept_invitation(body)
    return {"message": "Account created successfully. You can now log in."}
