"""
Exception hierarchy for the AI Platform Foundation.
"""

class AIError(Exception):
    """Base exception for all AI-related errors."""
    pass

class ProviderError(AIError):
    """Raised when the AI provider returns an error."""
    pass

class ProviderTimeoutError(ProviderError):
    """Raised when the AI provider times out."""
    pass

class RateLimitError(ProviderError):
    """Raised when the AI provider rate limit is exceeded."""
    pass

class AuthenticationError(ProviderError):
    """Raised when AI provider authentication fails."""
    pass

class ParsingError(AIError):
    """Raised when the AI response cannot be parsed into structured JSON."""
    pass

class WorkflowError(AIError):
    """Raised when an error occurs during workflow execution."""
    pass

class ToolExecutionError(AIError):
    """Raised when a tool execution fails."""
    pass

class ContextBuildError(AIError):
    """Raised when context building fails."""
    pass
