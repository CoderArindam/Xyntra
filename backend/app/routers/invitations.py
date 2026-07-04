import json
import logging
import secrets
import asyncpg
from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from app.schemas.invitations import (
    InviteUserRequest,
    InvitationResponse,
    AcceptInvitationRequest,
    InvitationDetailResponse,
)
from app.auth.dependencies import get_current_user
from app.auth.permissions import require_super_admin
from app.auth.password import get_password_hash
from app.database.connection import get_db_connection
from app.services.email_service import send_email
from app.config.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invitations", tags=["Invitations"])

INVITATION_EXPIRE_HOURS = 72
VALID_INVITE_ROLES = {"MEMBER", "MANAGER"}


def _send_invitation_email(to_email: str, org_name: str, token: str) -> None:
    frontend_url = settings.FRONTEND_ORIGINS.split(",")[0].strip()
    accept_url = f"{frontend_url}/accept-invitation?token={token}"
    body = (
        f"You have been invited to join {org_name} on ProSync.\n\n"
        f"Click the link below to accept your invitation and set up your account:\n\n"
        f"{accept_url}\n\n"
        f"This invitation expires in {INVITATION_EXPIRE_HOURS} hours.\n\n"
        f"If you did not expect this invitation, you can safely ignore this email."
    )
    send_email(
        to_email=to_email,
        subject=f"You're invited to join {org_name} on ProSync",
        body_text=body,
    )


@router.post("", response_model=InvitationResponse, status_code=201)
async def invite_user(
    invite_in: InviteUserRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_super_admin),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """SUPER_ADMIN invites a user to their organization."""
    if invite_in.role not in VALID_INVITE_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Invited users must be MEMBER or MANAGER.",
        )

    organization_id = current_user["organization_id"]
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=INVITATION_EXPIRE_HOURS)

    try:
        # Get org name for the email
        org_result = await conn.fetchval(
            "SELECT get_organization_by_id($1)", organization_id
        )
        org_data = json.loads(org_result) if isinstance(org_result, str) else org_result
        org_name = org_data["name"] if org_data else "your organization"

        result = await conn.fetchval(
            "SELECT create_invitation($1, $2, $3, $4, $5)",
            organization_id,
            invite_in.email,
            invite_in.role,
            token,
            expires_at,
        )
        invitation = json.loads(result) if isinstance(result, str) else result

        # Send email in background
        background_tasks.add_task(
            _send_invitation_email, invite_in.email, org_name, token
        )

        return invitation
    except asyncpg.exceptions.RaiseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating invitation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create invitation")


@router.get("", response_model=List[InvitationResponse])
async def list_invitations(
    current_user: dict = Depends(require_super_admin),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """List all invitations for this organization."""
    try:
        result = await conn.fetchval(
            "SELECT get_organization_invitations($1)",
            current_user["organization_id"],
        )
        return json.loads(result) if isinstance(result, str) else result
    except Exception as e:
        logger.error(f"Error listing invitations: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get("/verify/{token}", response_model=InvitationDetailResponse)
async def verify_invitation(
    token: str,
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Public endpoint — validates token and returns invitation metadata for the accept page."""
    result = await conn.fetchval("SELECT get_invitation_by_token($1)", token)
    if not result:
        raise HTTPException(status_code=404, detail="Invitation not found")

    invitation = json.loads(result) if isinstance(result, str) else result

    if invitation.get("accepted_at"):
        raise HTTPException(status_code=410, detail="Invitation has already been accepted")

    expires_at = datetime.fromisoformat(str(invitation["expires_at"]).replace("Z", "+00:00"))
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invitation has expired")

    return invitation


@router.post("/accept")
async def accept_invitation(
    body: AcceptInvitationRequest,
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Public endpoint — accepts an invitation and creates the user account."""
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    hashed_password = get_password_hash(body.password)
    try:
        result = await conn.fetchval(
            "SELECT accept_invitation($1, $2, $3, $4)",
            body.token,
            hashed_password,
            body.first_name,
            body.last_name,
        )
        if not result:
            raise HTTPException(status_code=400, detail="Failed to accept invitation")

        return {"message": "Account created successfully. You can now log in."}
    except asyncpg.exceptions.RaiseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error accepting invitation: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
