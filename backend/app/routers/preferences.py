from fastapi import APIRouter, Depends
from app.schemas.preferences import UserPreferencesResponse, UserPreferencesUpdate
from app.services.preferences import PreferencesService
from app.auth.dependencies import get_current_user
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/users/me/preferences", tags=["Preferences"])

@router.get("", response_model=UserPreferencesResponse)
async def get_my_preferences(current_user: dict = Depends(get_current_user)):
    return await PreferencesService.get_preferences(current_user["id"])

@router.patch("", response_model=UserPreferencesResponse)
async def update_my_preferences(
    updates: UserPreferencesUpdate,
    current_user: dict = Depends(get_current_user)
):
    return await PreferencesService.update_preferences(current_user["id"], updates)
