"""
AI Configuration helper module.
Wraps the main application configuration for AI-specific needs.
"""
from app.config.config import settings

def is_ai_enabled() -> bool:
    """Check if AI is globally enabled."""
    return settings.AI_ENABLED

def get_provider() -> str:
    """Get the configured AI provider."""
    return settings.AI_PROVIDER

def get_model() -> str:
    """Get the configured AI model."""
    return settings.AI_MODEL

def get_provider_api_key(provider: str) -> str | None:
    """Get the API key for a specific provider."""
    provider = provider.lower()
    if provider == "openai":
        return settings.OPENAI_API_KEY
    elif provider == "anthropic":
        return settings.ANTHROPIC_API_KEY
    elif provider == "gemini":
        return settings.GEMINI_API_KEY
    elif provider == "azure":
        return settings.AZURE_OPENAI_KEY
    return None
