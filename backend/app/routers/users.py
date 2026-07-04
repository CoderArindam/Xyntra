import logging
from typing import List
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.schemas.auth import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

from app.schemas.common import DataEnvelope

@router.get("", response_model=DataEnvelope[List[UserResponse]])
async def get_all_users(
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Returns all users scoped to the caller's organization."""
    organization_id = current_user.get("organization_id")
    if not organization_id:
        raise HTTPException(status_code=400, detail="No organization context found")
    try:
        rows = await conn.fetch(
            "SELECT id, email, first_name, last_name, avatar_url, role, organization_id FROM users WHERE organization_id = $1 AND deleted_at IS NULL",
            organization_id
        )
        return DataEnvelope(data=[dict(row) for row in rows])
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

from app.schemas.users import UserUpdate, ChangePassword
from app.services.storage_service import StorageService
from fastapi import UploadFile, File
from app.auth.password import verify_password, get_password_hash

@router.patch("/me", response_model=DataEnvelope[UserResponse])
async def update_me(
    payload: UserUpdate,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        # Use COALESCE to keep existing values if none are provided
        row = await conn.fetchrow(
            """
            UPDATE users
            SET 
                first_name = COALESCE($1::VARCHAR, first_name),
                last_name = COALESCE($2::VARCHAR, last_name),
                avatar_url = COALESCE($3::VARCHAR, avatar_url)
            WHERE id = $4
            RETURNING id, email, first_name, last_name, avatar_url, role, organization_id
            """,
            payload.first_name, payload.last_name, payload.avatar_url, current_user["id"]
        )
        return DataEnvelope(data=dict(row))
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")

@router.put("/me/password", status_code=204)
async def change_password(
    payload: ChangePassword,
    request: Request,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        hashed_password = await conn.fetchval("SELECT password_hash FROM users WHERE id = $1", current_user["id"])
        
        # We need to assume the password might be null if OAuth is added, but right now it isn't.
        if hashed_password and not verify_password(payload.current_password, hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect current password")
            
        new_hash = get_password_hash(payload.new_password)
        await conn.execute("UPDATE users SET password_hash = $1 WHERE id = $2", new_hash, current_user["id"])
        
        ip_address = request.client.host if request.client else "Unknown"
        await conn.execute(
            """
            INSERT INTO audit_logs (organization_id, user_id, action, entity_type, entity_id, ip_address)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            current_user.get("organization_id"), current_user["id"], "PASSWORD_CHANGED", "USER", current_user["id"], ip_address
        )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")

@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        # Save file to local storage
        url = await StorageService.save_avatar(file)
        
        # Update user avatar_url
        await conn.execute("UPDATE users SET avatar_url = $1 WHERE id = $2", url, current_user["id"])
        
        return DataEnvelope(data={"avatar_url": url})
    except Exception as e:
        logger.error(f"Error uploading avatar: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload avatar")

@router.delete("/me/avatar", status_code=204)
async def delete_avatar(
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        await conn.execute("UPDATE users SET avatar_url = NULL WHERE id = $1", current_user["id"])
        return None
    except Exception as e:
        logger.error(f"Error deleting avatar: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete avatar")

