from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type
from pydantic import BaseModel

from app.ai.prompts.registry import PromptRegistry
from app.ai.tools.base import BaseTool

class BaseAgent(ABC):
    """
    Abstract base class for AI Agents.
    Agents define their identity, required tools, and prompt logic.
    """
    name: str
    available_tools: List[Type[BaseTool]] = []
    
    @abstractmethod
    def build_messages(self, user_input: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build the message array to send to the Gateway/Provider.
        """
        pass
