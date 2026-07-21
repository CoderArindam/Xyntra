import json
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
                "SELECT * FROM fn_update_user_profile($1, $2::VARCHAR, $3::VARCHAR, $4::VARCHAR)",
                current_user["id"], payload.first_name, payload.last_name, payload.avatar_url
            )
            return dict(row)
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            raise HTTPException(status_code=500, detail="Failed to update profile")

    def parse_user_agent(self, ua_string: str) -> tuple[str, str, str]:
        ua = ua_string.lower()
        browser = "Unknown"
        if "chrome" in ua and "edg" not in ua:
            browser = "Chrome"
        elif "safari" in ua and "chrome" not in ua:
            browser = "Safari"
        elif "firefox" in ua:
            browser = "Firefox"
        elif "edg" in ua:
            browser = "Edge"
        
        platform = "Unknown"
        if "windows" in ua:
            platform = "Windows"
        elif "mac" in ua:
            platform = "macOS"
        elif "linux" in ua:
            platform = "Linux"
        elif "android" in ua:
            platform = "Android"
        elif "iphone" in ua or "ipad" in ua:
            platform = "iOS"
            
        return browser, platform, f"{browser} on {platform}"

    async def change_password(self, payload: ChangePassword, current_user: dict, ip_address: str, ua_string: str = "Unknown"):
        try:
            hashed_password = await self.conn.fetchval("SELECT password_hash FROM users WHERE id = $1", current_user["id"])
            
            if hashed_password and not verify_password(payload.current_password, hashed_password):
                raise HTTPException(status_code=400, detail="Incorrect current password")
                
            new_hash = get_password_hash(payload.new_password)
            await self.conn.execute("UPDATE users SET password_hash = $1 WHERE id = $2", new_hash, current_user["id"])
            
            browser, platform, _ = self.parse_user_agent(ua_string)
            await self.conn.execute(
                "SELECT fn_log_security_event($1, $2, $3, $4::entity_type_enum, $5, $6, $7::jsonb)",
                current_user.get("organization_id"),
                current_user["id"],
                "PASSWORD_CHANGED",
                "USER",
                current_user["id"],
                ip_address,
                json.dumps({"browser": browser, "platform": platform, "status": "Success"})
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