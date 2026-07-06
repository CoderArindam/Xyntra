import logging
from typing import List, Optional
import asyncpg
from fastapi import HTTPException, UploadFile

from app.schemas.auth import UserResponse
from app.schemas.users import UserUpdate, ChangePassword
from app.auth.password import verify_password, get_password_hash
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_all_users(self, current_user: dict) -> List[dict]:
        organization_id = current_user.get("organization_id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="No organization context found")
        try:
            rows = await self.conn.fetch(
                "SELECT id, email, first_name, last_name, avatar_url, role, organization_id FROM users WHERE organization_id = $1 AND deleted_at IS NULL",
                organization_id
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred")

    async def update_me(self, payload: UserUpdate, current_user: dict) -> dict:
        try:
            row = await self.conn.fetchrow(
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
            return dict(row)
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            raise HTTPException(status_code=500, detail="Failed to update profile")

    async def change_password(self, payload: ChangePassword, current_user: dict, ip_address: str):
        try:
            hashed_password = await self.conn.fetchval("SELECT password_hash FROM users WHERE id = $1", current_user["id"])
            
            if hashed_password and not verify_password(payload.current_password, hashed_password):
                raise HTTPException(status_code=400, detail="Incorrect current password")
                
            new_hash = get_password_hash(payload.new_password)
            await self.conn.execute("UPDATE users SET password_hash = $1 WHERE id = $2", new_hash, current_user["id"])
            
            await self.conn.execute(
                """
                INSERT INTO audit_logs (organization_id, user_id, action, entity_type, entity_id, ip_address)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                current_user.get("organization_id"), current_user["id"], "PASSWORD_CHANGED", "USER", current_user["id"], ip_address
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            raise HTTPException(status_code=500, detail="Failed to change password")

    async def upload_avatar(self, file: UploadFile, current_user: dict) -> str:
        try:
            url = await StorageService.save_avatar(file)
            await self.conn.execute("UPDATE users SET avatar_url = $1 WHERE id = $2", url, current_user["id"])
            return url
        except Exception as e:
            logger.error(f"Error uploading avatar: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload avatar")

    async def delete_avatar(self, current_user: dict):
        try:
            await self.conn.execute("UPDATE users SET avatar_url = NULL WHERE id = $1", current_user["id"])
        except Exception as e:
            logger.error(f"Error deleting avatar: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete avatar")