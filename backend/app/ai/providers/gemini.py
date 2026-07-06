from typing import Any, Dict, List, Optional
import google.generativeai as genai
from google.generativeai.types import content_types

from app.ai.providers.base import AIProvider
from app.ai.exceptions import ProviderError, AuthenticationError

class GeminiProvider(AIProvider):
    """Gemini implementation of the AIProvider interface."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        super().__init__(api_key, model)
        if not self.api_key:
            raise AuthenticationError("Gemini API key is missing.")
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model)

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Gemini format: [{'role': 'user'|'model', 'parts': [...]}]
        gemini_messages = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                continue

            if role == "tool":
                # Tool responses must be passed back to the model as "user" with function_response part
                import json
                try:
                    result_data = json.loads(msg.get("content", "{}"))
                    # Gemini strictly requires the response to be a dictionary (JSON object)
                    if not isinstance(result_data, dict):
                        result_data = {"result": result_data}
                except:
                    result_data = {"result": msg.get("content", "")}
                
                gemini_messages.append({
                    "role": "user",
                    "parts": [{
                        "function_response": {
                            "name": msg.get("name", "unknown"),
                            "response": result_data
                        }
                    }]
                })
                continue
                
            gemini_role = "model" if role == "assistant" else "user"
            
            if role == "assistant" and msg.get("tool_calls"):
                parts = []
                for tc in msg["tool_calls"]:
                    parts.append({
                        "function_call": {
                            "name": tc["name"],
                            "args": tc.get("args", {})
                        }
                    })
                gemini_messages.append({
                    "role": gemini_role,
                    "parts": parts
                })
                continue

            content = msg.get("content", "")
            gemini_messages.append({
                "role": gemini_role,
                "parts": [content]
            })
        return gemini_messages

    def _format_tools(self, tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        if not tools:
            return None
            
        def clean_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
            if not isinstance(schema, dict):
                return schema
            cleaned = {}
            for k, v in schema.items():
                if k in ["title", "default"]:
                    continue
                if isinstance(v, dict):
                    cleaned[k] = clean_schema(v)
                elif isinstance(v, list):
                    cleaned[k] = [clean_schema(item) if isinstance(item, dict) else item for item in v]
                else:
                    cleaned[k] = v
            return cleaned

        func_decls = []
        for tool in tools:
            func = tool.get("function", {})
            params = func.get("parameters", {})
            func_decls.append({
                "name": func.get("name"),
                "description": func.get("description"),
                "parameters": clean_schema(params)
            })
        return [{"function_declarations": func_decls}]

    def generate(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        response_format: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a response using Gemini API.
        """
        system_instruction = "\n".join([m["content"] for m in messages if m["role"] == "system"])
        history = self._convert_messages([m for m in messages if m["role"] != "system"])

        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_instruction if system_instruction else None,
            tools=self._format_tools(tools)
        )

        config_kwargs = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if response_format:
            config_kwargs["response_mime_type"] = "application/json"

        generation_config = genai.types.GenerationConfig(**config_kwargs)

        try:
            response = model.generate_content(
                contents=history,
                generation_config=generation_config
            )
            
            content = ""
            tool_calls = []
            
            if response.candidates:
                candidate = response.candidates[0]
                for part in candidate.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        tool_calls.append({
                            "name": part.function_call.name,
                            "args": dict(part.function_call.args)
                        })
                    elif hasattr(part, "text"):
                        content += part.text
            
            return {
                "content": content,
                "tool_calls": tool_calls,
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
        except Exception as e:
            raise ProviderError(f"Gemini API Error: {str(e)}")

    def stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Stream a response using Gemini API.
        """
        system_instruction = "\n".join([m["content"] for m in messages if m["role"] == "system"])
        history = self._convert_messages([m for m in messages if m["role"] != "system"])

        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_instruction if system_instruction else None,
            tools=self._format_tools(tools)
        )

        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        try:
            from google.api_core import retry
            response = model.generate_content(
                contents=history,
                generation_config=generation_config,
                stream=True,
                request_options={"retry": retry.Retry(initial=1.0, maximum=1.0, multiplier=1.0, deadline=2.0)} if hasattr(genai.types, "RequestOptions") else None
            )
            
            for chunk in response:
                if chunk.candidates and chunk.candidates[0].content.parts:
                    part = chunk.candidates[0].content.parts[0]
                    if hasattr(part, "function_call") and part.function_call:
                        yield {
                            "tool_calls": [{
                                "name": part.function_call.name,
                                "args": dict(part.function_call.args)
                            }]
                        }
                    elif hasattr(part, "text"):
                        yield {"content": part.text}
        except Exception as e:
            raise ProviderError(f"Gemini API Streaming Error: {str(e)}")

    def embeddings(self, text: str) -> List[float]:
        return [0.0] * 1536

    def health_check(self) -> bool:
        return bool(self.api_key)
