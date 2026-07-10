from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from app.ai.tools.base import BaseTool, RiskLevel
from app.schemas.preferences import ThemeEnum, UserPreferencesUpdate

class UpdateAppearanceParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
    theme: Optional[ThemeEnum] = Field(None, description="The preferred theme mode (light, dark, system)")
    accent_color: Optional[str] = Field(None, description="The accent color name (blue, indigo, emerald, rose, amber)")
    sidebar_theme: Optional[str] = Field(None, description="The sidebar visual theme (default, tinted, dark)")
    sidebar_collapsed: Optional[bool] = Field(None, description="Whether the sidebar should be collapsed (true) or expanded (false)")
    reset_defaults: Optional[bool] = Field(False, description="Whether to restore default appearance settings")

class UpdateAppearanceTool(BaseTool):
    """
    Updates the user's appearance preferences (theme, accent color, sidebar appearance).
    Automatically maps common color names to valid options (e.g., purple -> indigo).
    """
    name = "update_appearance"
    description = "Update the current user's appearance preferences: theme (light/dark/system), accent color, sidebar theme, or sidebar collapsed state."
    action = "update_appearance"
    category = "appearance"
    risk_level = RiskLevel.SAFE
    is_write_action = True
    input_schema = UpdateAppearanceParams

    async def execute(self, params: UpdateAppearanceParams, current_user: dict, services: Dict[str, Any]) -> Any:
        preferences_service = services.get("preferences_service")
        if not preferences_service:
            raise ValueError("preferences_service is not available")

        theme = params.theme
        accent_color = params.accent_color
        sidebar_theme = params.sidebar_theme
        sidebar_collapsed = params.sidebar_collapsed

        if params.reset_defaults:
            theme = ThemeEnum.system
            accent_color = "blue"
            sidebar_theme = "default"
            sidebar_collapsed = False

        if accent_color:
            accent_color = accent_color.lower().strip()
            mapping = {"purple": "indigo", "green": "emerald", "red": "rose", "yellow": "amber", "orange": "amber"}
            accent_color = mapping.get(accent_color, accent_color)

        updated_prefs = await preferences_service.update_preferences(
            user_id=current_user["id"],
            updates=UserPreferencesUpdate(
                theme=theme,
                accent_color=accent_color,
                sidebar_theme=sidebar_theme,
                sidebar_collapsed=sidebar_collapsed,
            )
        )

        prefs_dict = updated_prefs.model_dump()
        return {
            "status": "success",
            "action": "appearance_updated",
            "message": "Appearance preferences updated.",
            "verified": {
                "theme": prefs_dict.get("theme"),
                "accent_color": prefs_dict.get("accent_color"),
                "sidebar_theme": prefs_dict.get("sidebar_theme"),
                "sidebar_collapsed": prefs_dict.get("sidebar_collapsed")
            }
        }

class GetMyAppearanceParams(BaseModel):
    pass

class GetMyAppearanceTool(BaseTool):
    """Retrieves the user's current appearance preferences."""
    name = "get_my_appearance"
    description = "Retrieve the current user's appearance preferences (theme, accent color, sidebar theme, sidebar state)."
    action = "get_my_appearance"
    category = "appearance"
    risk_level = RiskLevel.SAFE
    is_write_action = False
    input_schema = GetMyAppearanceParams

    async def execute(self, params: GetMyAppearanceParams, current_user: dict, services: Dict[str, Any]) -> Any:
        preferences_service = services.get("preferences_service")
        if not preferences_service:
            raise ValueError("preferences_service is not available")

        prefs = await preferences_service.get_preferences(current_user["id"])
        if not prefs:
            return {"status": "error", "message": "Preferences not found."}

        prefs_dict = prefs.model_dump()
        return {
            "status": "success",
            "action": "appearance_fetched",
            "verified": {
                "theme": prefs_dict.get("theme"),
                "accent_color": prefs_dict.get("accent_color"),
                "sidebar_theme": prefs_dict.get("sidebar_theme"),
                "sidebar_collapsed": prefs_dict.get("sidebar_collapsed")
            }
        }
