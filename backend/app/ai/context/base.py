from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseContextBuilder(ABC):
    """
    Abstract base class for building AI context.
    Context builders retrieve information via Services to inject into Prompts.
    """
    @abstractmethod
    async def build(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Build and return the context dictionary.
        """
        pass
