from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from google import genai

if TYPE_CHECKING:
    # pyrefly: ignore [missing-import]
    from google.genai import types as genai_types
else:
    genai_types = genai.types

from app.ai.providers.base import AIProvider
from app.ai.exceptions import ProviderError, AuthenticationError


class GeminiProvider(AIProvider):
    """Gemini implementation of the AIProvider interface using google.genai."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        super().__init__(api_key, model)
        if not self.api_key:
            raise AuthenticationError("Gemini API key is missing.")
        self.client = genai.Client(api_key=self.api_key)

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[genai_types.Content]:
        contents = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                continue

            if role == "tool":
                import json
                try:
                    result_data = json.loads(msg.get("content", "{}"))
                    if not isinstance(result_data, dict):
                        result_data = {"result": result_data}
                except Exception:
                    result_data = {"result": msg.get("content", "")}

                contents.append(genai_types.Content(
                    role="user",
                    parts=[genai_types.Part(
                        function_response=genai_types.FunctionResponse(
                            name=msg.get("name", "unknown"),
                            response=result_data
                        )
                    )]
                ))
                continue

            gemini_role = "model" if role == "assistant" else "user"

            if role == "assistant" and msg.get("tool_calls"):
                parts = [
                    genai_types.Part(
                        function_call=genai_types.FunctionCall(
                            name=tc["name"],
                            args=tc.get("args", {})
                        )
                    )
                    for tc in msg["tool_calls"]
                ]
                contents.append(genai_types.Content(role=gemini_role, parts=parts))
                continue

            contents.append(genai_types.Content(
                role=gemini_role,
                parts=[genai_types.Part(text=msg.get("content", ""))]
            ))
        return contents

    def _format_tools(self, tools: Optional[List[Dict[str, Any]]]) -> Optional[List[genai_types.Tool]]:
        if not tools:
            return None

        def clean_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
            if not isinstance(schema, dict):
                return schema
            return {
                k: clean_schema(v) if isinstance(v, dict)
                else [clean_schema(i) if isinstance(i, dict) else i for i in v] if isinstance(v, list)
                else v
                for k, v in schema.items()
                if k not in ("title", "default")
            }

        func_decls = [
            genai_types.FunctionDeclaration(
                name=tool.get("function", {}).get("name"),
                description=tool.get("function", {}).get("description"),
                parameters=clean_schema(tool.get("function", {}).get("parameters", {}))
            )
            for tool in tools
        ]
        return [genai_types.Tool(function_declarations=func_decls)]

    def _system_instruction(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        parts = [m["content"] for m in messages if m["role"] == "system"]
        return "\n".join(parts) if parts else None

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        response_format: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        contents = self._convert_messages(messages)
        system = self._system_instruction(messages)

        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system,
            tools=self._format_tools(tools),
        )
        if response_format:
            config.response_mime_type = "application/json"

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

            content = ""
            tool_calls = []
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        tool_calls.append({
                            "name": part.function_call.name,
                            "args": dict(part.function_call.args)
                        })
                    elif part.text:
                        content += part.text

            return {
                "content": content,
                "tool_calls": tool_calls,
                "usage": {
                    "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                    "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
                    "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
                }
            }
        except Exception as e:
            raise ProviderError(f"Gemini API Error: {str(e)}")

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        contents = self._convert_messages(messages)
        system = self._system_instruction(messages)

        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system,
            tools=self._format_tools(tools),
        )

        try:
            async for chunk in await self.client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=config,
            ):
                if not chunk.candidates:
                    continue
                for part in chunk.candidates[0].content.parts:
                    if part.function_call:
                        yield {
                            "tool_calls": [{
                                "name": part.function_call.name,
                                "args": dict(part.function_call.args)
                            }]
                        }
                    elif part.text:
                        yield {"content": part.text}
        except Exception as e:
            raise ProviderError(f"Gemini API Streaming Error: {str(e)}")

    def embeddings(self, text: str) -> List[float]:
        return [0.0] * 1536

    def health_check(self) -> bool:
        return bool(self.api_key)
