import logging
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, ValidationError

from app.ai.config.settings import ai_settings
from app.ai.exceptions import AIError, ProviderError, ParsingError, PermissionError
from app.ai.providers.base import AIProvider
from app.ai.providers.openai import OpenAIProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.puter import PuterProvider
from app.ai.telemetry.context import Span, TraceContext
from app.ai.telemetry.bus import telemetry_bus
from app.ai.telemetry.events import EventType
import time
import json

logger = logging.getLogger("ai.gateway")

class AIGateway:
    """Central AI Gateway responsible for routing, retries, rate limiting, and telemetry."""
    
    def __init__(self):
        self.provider_name = ai_settings.AI_PROVIDER
        self.model_name = ai_settings.AI_MODEL
        self.provider = self._init_provider()
        
    def _init_provider(self) -> AIProvider:
        api_key = self._get_provider_api_key(self.provider_name) or ""
        if self.provider_name.lower() == "openai":
            return OpenAIProvider(api_key=api_key, model=self.model_name)
        elif self.provider_name.lower() == "gemini":
            return GeminiProvider(api_key=api_key, model=self.model_name)
        elif self.provider_name.lower() == "puter":
            return PuterProvider(api_key=api_key, model=self.model_name)
        else:
            return GeminiProvider(api_key=api_key, model=self.model_name)

    @staticmethod
    def _get_provider_api_key(provider: str) -> str | None:
        provider = provider.lower()
        if provider == "openai":
            return ai_settings.OPENAI_API_KEY
        elif provider == "anthropic":
            return ai_settings.ANTHROPIC_API_KEY
        elif provider == "gemini":
            return ai_settings.GEMINI_API_KEY
        elif provider == "azure":
            return ai_settings.AZURE_OPENAI_KEY
        elif provider == "puter":
            return ai_settings.PUTER_API_KEY
        return None

    def _check_feature_flags(self, org_ai_enabled: bool = True, user_has_permission: bool = True):
        if not ai_settings.AI_ENABLED:
            raise AIError("AI features are globally disabled.")
        if not org_ai_enabled:
            raise AIError("AI features are disabled for this organization.")
        if not user_has_permission:
            raise PermissionError("You do not have permission to use AI features.")

    async def execute_prompt(
        self,
        messages: List[Dict[str, Any]],
        org_ai_enabled: bool = True,
        user_has_permission: bool = True,
        response_schema: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        workflow_id: Optional[str] = None,
        request_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Any:
        self._check_feature_flags(org_ai_enabled, user_has_permission)

        with Span("LLM Call", "AIGateway") as span:
            span.metadata["provider"] = self.provider_name
            span.metadata["model"] = self.model_name
            span.metadata["workflow_id"] = workflow_id
            
            async def do_call():
                response = await self.provider.generate(
                    messages=messages,
                    temperature=ai_settings.AI_TEMPERATURE,
                    max_tokens=ai_settings.AI_MAX_TOKENS,
                    tools=tools
                )
                
                content = response.get("content")
                usage = response.get("usage", {})
                
                span.metadata["prompt_tokens"] = usage.get("prompt_tokens", 0)
                span.metadata["completion_tokens"] = usage.get("completion_tokens", 0)
                span.metadata["total_tokens"] = usage.get("total_tokens", 0)
                
                TraceContext.increment_metric("total_llm_calls")
                TraceContext.increment_metric("total_tokens", usage.get("total_tokens", 0))
                
                if response_schema and content:
                    try:
                        try:
                            parsed_json = json.loads(content)
                            validated_output = response_schema.model_validate(parsed_json)
                        except json.JSONDecodeError:
                            clean_content = content.strip()
                            if clean_content.startswith("```json"):
                                clean_content = clean_content[7:]
                            elif clean_content.startswith("```"):
                                clean_content = clean_content[3:]
                            if clean_content.endswith("```"):
                                clean_content = clean_content[:-3]
                            
                            try:
                                parsed_json = json.loads(clean_content.strip())
                            except json.JSONDecodeError:
                                # Advanced repair: extract everything between first { and last }
                                start = clean_content.find('{')
                                end = clean_content.rfind('}')
                                if start != -1 and end != -1 and end > start:
                                    repaired = clean_content[start:end+1]
                                    parsed_json = json.loads(repaired)
                                else:
                                    raise
                                    
                            validated_output = response_schema.model_validate(parsed_json)
                            
                        return validated_output
                    except ValidationError as ve:
                        raise ParsingError(f"Failed to parse LLM output: Schema validation failed. {str(ve)}", content=content)
                    except Exception as pe:
                        raise ParsingError(f"Failed to parse LLM output: Response is not valid JSON. {str(pe)}", content=content)
                        
                return response
                
            def on_parsing_error(e: ParsingError):
                content = getattr(e, "content", "")
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": f"Your last response was not valid according to the schema. Please fix it. Error: {str(e)}"})
                
            from app.ai.gateway.retries import RetryPolicy
            policy = RetryPolicy()
            return await policy.execute_async(
                func=do_call,
                request_id=request_id,
                span_id=span.span_id,
                parent_span_id=span.parent_span_id,
                on_parsing_error=on_parsing_error
            )

    async def stream_prompt(
        self,
        messages: List[Dict[str, Any]],
        org_ai_enabled: bool,
        user_has_permission: bool,
        tools: Optional[List[Dict[str, Any]]] = None,
        workflow_id: Optional[str] = None,
        request_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Any:
        self._check_feature_flags(org_ai_enabled, user_has_permission)
        
        with Span("LLM Stream", "AIGateway") as span:
            span.metadata["provider"] = self.provider_name
            span.metadata["model"] = self.model_name
            span.metadata["workflow_id"] = workflow_id
            
            try:
                stream_gen = self.provider.stream(
                    messages=messages,
                    temperature=ai_settings.AI_TEMPERATURE,
                    max_tokens=ai_settings.AI_MAX_TOKENS,
                    tools=tools
                )
                
                TraceContext.increment_metric("total_llm_calls")
                
                async for chunk in stream_gen:
                    yield chunk
                    
            except ProviderError as e:
                raise e