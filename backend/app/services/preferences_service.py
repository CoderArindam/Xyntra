from fastapi import HTTPException, status
import asyncpg
from app.schemas.preferences import UserPreferencesResponse, UserPreferencesUpdate

class PreferencesService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_preferences(self, user_id: int) -> UserPreferencesResponse:
        row = await self.conn.fetchrow(
            "SELECT * FROM fn_get_user_preferences($1)",
            user_id
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User preferences not found"
            )
        return UserPreferencesResponse(**dict(row))

    async def update_preferences(self, user_id: int, updates: UserPreferencesUpdate) -> UserPreferencesResponse:
        update_data = updates.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_preferences(user_id)

        row = await self.conn.fetchrow(
            """
            SELECT * FROM fn_update_user_preferences(
                $1,
                p_theme := $2::theme_enum,
                p_accent_color := $3,
                p_sidebar_theme := $4,
                p_sidebar_collapsed := $5
            )
            """,
            user_id,
            update_data.get('theme'),
            update_data.get('accent_color'),
            update_data.get('sidebar_theme'),
            update_data.get('sidebar_collapsed')
        )

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User preferences not found or update failed"
            )
        return UserPreferencesResponse(**dict(row))