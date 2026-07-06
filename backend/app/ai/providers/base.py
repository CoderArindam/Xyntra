from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class AIProvider(ABC):
    """Base interface for all AI Providers."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        response_format: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a response from the LLM.
        Returns a dictionary containing the response content, tool calls, and usage stats.
        """
        pass

    @abstractmethod
    def stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Stream a response from the LLM.
        Yields chunks of the response.
        """
        pass

    @abstractmethod
    def embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for a given text (stub for future).
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the provider is healthy and accessible.
        """
        pass
