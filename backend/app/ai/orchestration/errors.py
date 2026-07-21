from typing import Dict
from app.ai.exceptions import AIError, FailureCategory

class ErrorMessageFactory:
    """
    Data-driven factory mapping internal AI exceptions to graceful user-facing messages.
    Never exposes raw exceptions, stack traces, or malformed JSON to the user.
    """
    
    _templates: Dict[FailureCategory, str] = {
        FailureCategory.USER_ERROR: "I couldn't complete that because of a problem with the request. Please modify it and try again.",
        FailureCategory.VALIDATION_ERROR: "The provided instructions couldn't be validated. Please check the details and try again.",
        FailureCategory.PERMISSION_ERROR: "You don't have permission to perform this action.",
        FailureCategory.AI_PROVIDER_ERROR: "The AI service is experiencing an issue. Please try again later.",
        FailureCategory.PARSING_ERROR: "I had trouble understanding the response format. Please try your request again.",
        FailureCategory.INFRASTRUCTURE_ERROR: "There was a system error while processing your request. We're looking into it.",
        FailureCategory.BUSINESS_LOGIC_ERROR: "The operation failed due to a problem executing the task.",
        FailureCategory.TEMPORARY_FAILURE: "The service is temporarily busy. Please try again in a few moments.",
        FailureCategory.PERMANENT_FAILURE: "I encountered an error and couldn't complete your request.",
    }

    @classmethod
    def get_user_message(cls, error: Exception) -> str:
        """
        Derives a safe user-facing error message from an exception.
        """
        if isinstance(error, AIError):
            if getattr(error, "message", None):
                return error.message
            return cls._templates.get(error.category, cls._templates[FailureCategory.PERMANENT_FAILURE])
        
        # Fallback for unexpected generic exceptions
        return cls._templates[FailureCategory.INFRASTRUCTURE_ERROR]
