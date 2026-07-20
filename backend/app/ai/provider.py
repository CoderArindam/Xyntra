"""AI Provider abstraction facade."""

from app.ai.gateway.ai_gateway import AIGateway
from app.ai.config.settings import ai_settings

def get_ai_provider() -> AIGateway:
    """Returns the configured AI gateway instance."""
    return AIGateway()
