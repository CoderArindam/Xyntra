from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseWorkflow(ABC):
    """
    Abstract base class for AI Workflows.
    Workflows orchestrate multiple agents, tools, and services to achieve complex tasks.
    """
    
    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """
        Execute the workflow.
        """
        pass
