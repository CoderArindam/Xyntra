from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class BaseMemory(ABC):
    """Interface for Memory Storage."""

    @abstractmethod
    def add_message(self, session_id: str, role: str, content: str):
        pass

    @abstractmethod
    def get_messages(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        pass

    @abstractmethod
    def clear(self, session_id: str):
        pass

class ConversationMemory(BaseMemory):
    """Implementation-agnostic conversation memory."""
    pass

class WorkspaceMemory(BaseMemory):
    """Implementation-agnostic workspace context memory (e.g. vector store later)."""
    pass
