from fastapi import HTTPException, status
from app.database.connection import get_db_connection
from app.schemas.preferences import UserPreferencesResponse, UserPreferencesUpdate

class PreferencesService:
    @staticmethod
    async def get_preferences(user_id: int) -> UserPreferencesResponse:
        async for conn in get_db_connection():
            row = await conn.fetchrow(
                "SELECT * FROM fn_get_user_preferences($1)",
                user_id
            )
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User preferences not found"
                )
            return UserPreferencesResponse(**dict(row))

    @staticmethod
    async def update_preferences(user_id: int, updates: UserPreferencesUpdate) -> UserPreferencesResponse:
        async for conn in get_db_connection():
            update_data = updates.model_dump(exclude_unset=True)
            if not update_data:
                # If no updates, just return current
                return await PreferencesService.get_preferences(user_id)
            
            row = await conn.fetchrow(
                """
                SELECT * FROM fn_update_user_preferences(
                    $1,
                    p_theme := $2::theme_enum,
                    p_accent_color := $3,
                    p_sidebar_theme := $4
                )
                """,
                user_id,
                update_data.get('theme'),
                update_data.get('accent_color'),
                update_data.get('sidebar_theme')
            )
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User preferences not found or update failed"
                )
            return UserPreferencesResponse(**dict(row))
