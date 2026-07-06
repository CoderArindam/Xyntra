"""
Exception hierarchy for the AI Platform Foundation.
"""
from enum import Enum
from typing import Optional, Dict, Any

class FailureCategory(str, Enum):
    USER_ERROR = "USER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    AI_PROVIDER_ERROR = "AI_PROVIDER_ERROR"
    PARSING_ERROR = "PARSING_ERROR"
    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"
    BUSINESS_LOGIC_ERROR = "BUSINESS_LOGIC_ERROR"
    TEMPORARY_FAILURE = "TEMPORARY_FAILURE"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"

class AIError(Exception):
    """Base exception for all AI-related errors."""
    def __init__(self, message: str, category: FailureCategory = FailureCategory.PERMANENT_FAILURE, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.category = category
        self.details = details or {}

class ProviderError(AIError):
    """Raised when the AI provider returns an error."""
    def __init__(self, message: str, is_retryable: bool = True, details: Optional[Dict[str, Any]] = None):
        category = FailureCategory.TEMPORARY_FAILURE if is_retryable else FailureCategory.AI_PROVIDER_ERROR
        super().__init__(message, category=category, details=details)
        self.is_retryable = is_retryable

class ProviderTimeoutError(ProviderError):
    """Raised when the AI provider times out."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, is_retryable=True, details=details)

class ExecutionTimeoutError(AIError):
    """Raised when an execution stage times out."""
    def __init__(self, message: str, stage: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["stage"] = stage
        super().__init__(message, category=FailureCategory.TEMPORARY_FAILURE, details=details)

class ParsingError(AIError):
    """Raised when the AI response cannot be parsed into structured JSON."""
    def __init__(self, message: str, content: str = ""):
        super().__init__(message, category=FailureCategory.PARSING_ERROR, details={"content": content})
        self.content = content

class PlannerError(AIError):
    """Raised when planning fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, category=FailureCategory.PERMANENT_FAILURE, details=details)

class ValidationError(AIError):
    """Raised when plan or input validation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, category=FailureCategory.VALIDATION_ERROR, details=details)

class ToolResolutionError(AIError):
    """Raised when a tool cannot be resolved or found."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, category=FailureCategory.PERMANENT_FAILURE, details=details)

class ToolExecutionError(AIError):
    """Raised when a tool execution fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, category=FailureCategory.BUSINESS_LOGIC_ERROR, details=details)

class PermissionError(AIError):
    """Raised when user lacks permission to execute an action."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, category=FailureCategory.PERMISSION_ERROR, details=details)

class AuthenticationError(AIError):
    """Raised when authentication with an AI provider fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, category=FailureCategory.INFRASTRUCTURE_ERROR, details=details)

class ContextError(AIError):
    """Raised when context building fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, category=FailureCategory.PERMANENT_FAILURE, details=details)

class RetryLimitExceededError(AIError):
    """Raised when maximum retries are exceeded."""
    def __init__(self, message: str, original_error: Exception, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["original_error"] = str(original_error)
        super().__init__(message, category=FailureCategory.PERMANENT_FAILURE, details=details)
        self.original_error = original_error

class UserCancellationError(AIError):
    """Raised when execution is cancelled by the user."""
    def __init__(self, message: str = "Execution cancelled by user."):
        super().__init__(message, category=FailureCategory.USER_ERROR)
