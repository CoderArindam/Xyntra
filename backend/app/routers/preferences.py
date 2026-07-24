from fastapi import APIRouter, Depends
from app.schemas.preferences import UserPreferencesResponse, UserPreferencesUpdate
from app.services.preferences_service import PreferencesService
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection

router = APIRouter(prefix="/users/me/preferences", tags=["Preferences"])


def get_pref_service(conn = Depends(get_db_connection)) -> PreferencesService:
    return PreferencesService(conn)

@router.get("", response_model=UserPreferencesResponse)
async def get_my_preferences(
    current_user: dict = Depends(get_current_user),
    pref_service: PreferencesService = Depends(get_pref_service)
):
    return await pref_service.get_preferences(current_user["id"])

@router.patch("", response_model=UserPreferencesResponse)
async def update_my_preferences(
    updates: UserPreferencesUpdate,
    current_user: dict = Depends(get_current_user),
    pref_service: PreferencesService = Depends(get_pref_service)
):
    return await pref_service.update_preferences(current_user["id"], updates)
