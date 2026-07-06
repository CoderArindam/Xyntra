from typing import Any, Dict, List, Optional
from app.ai.providers.base import AIProvider
from app.ai.exceptions import ProviderError, AuthenticationError
from openai import AsyncOpenAI
import json

class OpenAIProvider(AIProvider):
    """OpenAI implementation of the AIProvider interface."""
    
    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        if not self.api_key:
            raise AuthenticationError("OpenAI API key is missing.")
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        response_format: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a response using OpenAI API.
        """
        if not self.api_key:
            raise AuthenticationError("OpenAI API key is missing.")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": 15.0
        }
        
        if response_format:
            # We assume response_format is a json schema or {"type": "json_object"}
            kwargs["response_format"] = {"type": "json_object"}
            
        if tools:
            formatted_tools = []
            for tool in tools:
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool.get("parameters", {})
                    }
                })
            kwargs["tools"] = formatted_tools

        try:
            response = await self.client.chat.completions.create(**kwargs)
            
            message = response.choices[0].message
            content = message.content or ""
            
            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    if tc.type == "function":
                        tool_calls.append({
                            "name": tc.function.name,
                            "args": json.loads(tc.function.arguments)
                        })
                        
            return {
                "content": content,
                "tool_calls": tool_calls,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except Exception as e:
            raise ProviderError(f"OpenAI API Error: {str(e)}")

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        """Stream response using OpenAI API."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "timeout": 15.0
        }
        
        try:
            stream = await self.client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield {"content": delta.content}
        except Exception as e:
            raise ProviderError(f"OpenAI Stream Error: {str(e)}")

    def embeddings(self, text: str) -> List[float]:
        """Mock embeddings."""
        return [0.0] * 1536

    def health_check(self) -> bool:
        """Health check."""
        return bool(self.api_key)
