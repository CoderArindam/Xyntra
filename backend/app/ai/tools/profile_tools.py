from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from app.ai.tools.base import BaseTool, RiskLevel
from app.schemas.users import UserUpdate

class UpdateProfileParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
    first_name: Optional[str] = Field(None, description="The user's new first name")
    last_name: Optional[str] = Field(None, description="The user's new last name")

class UpdateProfileTool(BaseTool):
    """Updates the user's profile information (first name, last name)."""
    name = "update_profile"
    description = "Update the current user's profile information such as first name or last name."
    action = "update_profile"
    category = "profile"
    risk_level = RiskLevel.SAFE
    is_write_action = True
    input_schema = UpdateProfileParams

    async def execute(self, params: UpdateProfileParams, current_user: dict, services: Dict[str, Any]) -> Any:
        user_service = services.get("user_service")
        if not user_service:
            raise ValueError("user_service is not available")

        updates = UserUpdate(
            first_name=params.first_name if params.first_name is not None else current_user.get("first_name"),
            last_name=params.last_name if params.last_name is not None else current_user.get("last_name")
        )

        updated_user = await user_service.update_me(updates, current_user)

        return {
            "status": "success",
            "action": "profile_updated",
            "message": "Profile updated successfully.",
            "verified": {
                "first_name": updated_user.get("first_name"),
                "last_name": updated_user.get("last_name"),
                "email": updated_user.get("email")
            }
        }

class GetMyProfileParams(BaseModel):
    pass

class GetMyProfileTool(BaseTool):
    """Retrieves the user's current profile information (first name, last name, email)."""
    name = "get_my_profile"
    description = "Retrieve the current user's profile information (first name, last name, email)."
    action = "get_my_profile"
    category = "profile"
    risk_level = RiskLevel.SAFE
    is_write_action = False
    input_schema = GetMyProfileParams

    async def execute(self, params: GetMyProfileParams, current_user: dict, services: Dict[str, Any]) -> Any:
        return {
            "status": "success",
            "action": "profile_fetched",
            "verified": {
                "first_name": current_user.get("first_name"),
                "last_name": current_user.get("last_name"),
                "email": current_user.get("email")
            }
        }
