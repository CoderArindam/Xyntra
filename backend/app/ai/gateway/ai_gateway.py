import logging
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, ValidationError

from app.config.config import settings
from app.ai.config import is_ai_enabled, get_provider, get_model, get_provider_api_key
from app.ai.exceptions import AIError, ProviderError, ParsingError
from app.ai.providers.base import AIProvider
from app.ai.providers.openai import OpenAIProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.telemetry.tracker import TelemetryEvent

logger = logging.getLogger("ai.gateway")

class AIGateway:
    """
    Central AI Gateway responsible for routing, retries, rate limiting, and telemetry.
    Designed to be injected via Dependency Injection.
    """
    
    def __init__(self):
        self.provider_name = get_provider()
        self.model_name = get_model()
        self.provider = self._init_provider()
        
    def _init_provider(self) -> AIProvider:
        api_key = get_provider_api_key(self.provider_name) or ""
        if self.provider_name.lower() == "openai":
            return OpenAIProvider(api_key=api_key, model=self.model_name)
        elif self.provider_name.lower() == "gemini":
            return GeminiProvider(api_key=api_key, model=self.model_name)
        else:
            # Fallback
            return GeminiProvider(api_key=api_key, model=self.model_name)

    def _check_feature_flags(self, org_ai_enabled: bool, user_has_permission: bool):
        if not is_ai_enabled():
            raise AIError("AI features are globally disabled.")
        if not org_ai_enabled:
            raise AIError("AI features are disabled for this organization.")
        if not user_has_permission:
            raise AIError("User does not have permission to use AI features.")

    def execute_prompt(
        self,
        messages: List[Dict[str, Any]],
        org_ai_enabled: bool,
        user_has_permission: bool,
        response_schema: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        workflow_id: Optional[str] = None,
        request_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Any:
        """
        Executes a prompt against the configured provider, tracking telemetry and validating output.
        """
        self._check_feature_flags(org_ai_enabled, user_has_permission)

        telemetry = TelemetryEvent(
            provider=self.provider_name,
            model=self.model_name,
            workflow_id=workflow_id,
            request_id=request_id,
            organization_id=organization_id,
            user_id=user_id,
        )

        retries = 0
        max_retries = settings.AI_MAX_RETRIES

        while retries <= max_retries:
            try:
                # Add tools tracking to telemetry if applicable
                if tools:
                    telemetry.add_tool_call()

                # Call provider
                response = self.provider.generate(
                    messages=messages,
                    temperature=settings.AI_TEMPERATURE,
                    max_tokens=settings.AI_MAX_TOKENS,
                    tools=tools
                )
                
                content = response.get("content")
                usage = response.get("usage", {})
                
                # Structured output validation
                if response_schema and content:
                    try:
                        # In reality, the LLM might return JSON string, so we'd parse it.
                        # For Phase 1 we assume the mock/SDK handles json.loads if structured.
                        # Mocking validation here:
                        import json
                        try:
                            parsed_json = json.loads(content)
                            validated_output = response_schema.model_validate(parsed_json)
                        except json.JSONDecodeError:
                            # if not JSON, wrap it for testing or raise
                            raise ValueError("Response is not valid JSON.")
                    except (ValidationError, ValueError) as e:
                        if retries < max_retries:
                            retries += 1
                            telemetry.add_retry()
                            # Retry logic with repair prompt would go here
                            messages.append({"role": "assistant", "content": content})
                            messages.append({"role": "user", "content": f"Failed to parse JSON. Error: {e}. Please fix and return valid JSON."})
                            continue
                        else:
                            telemetry.record_failure("ParsingError")
                            raise ParsingError(f"Failed to parse LLM output: {str(e)}")
                else:
                    validated_output = content

                # Record Success
                telemetry.record_success(
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    estimated_cost=0.0 # Calculate based on model later
                )
                
                return validated_output

            except ProviderError as e:
                telemetry.record_failure(str(e))
                raise
            except Exception as e:
                telemetry.record_failure(str(e))
                raise AIError(f"Unexpected AI execution error: {str(e)}")

    def stream_prompt(
        self,
        messages: List[Dict[str, Any]],
        org_ai_enabled: bool,
        user_has_permission: bool,
        tools: Optional[List[Dict[str, Any]]] = None,
        workflow_id: Optional[str] = None,
        request_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """
        Streams a prompt against the configured provider.
        Yields chunks, handles telemetry and tools.
        """
        self._check_feature_flags(org_ai_enabled, user_has_permission)

        telemetry = TelemetryEvent(
            provider=self.provider_name,
            model=self.model_name,
            workflow_id=workflow_id,
            request_id=request_id,
            conversation_id=conversation_id,
            organization_id=organization_id,
            user_id=user_id,
        )

        try:
            if tools:
                telemetry.add_tool_call()

            stream_gen = self.provider.stream(
                messages=messages,
                temperature=settings.AI_TEMPERATURE,
                max_tokens=settings.AI_MAX_TOKENS,
                tools=tools
            )
            
            # Since stream is a generator, we yield from it, but we can't record success until it finishes.
            # We will yield chunks and when done, record success.
            for chunk in stream_gen:
                yield chunk
            
            telemetry.record_success(prompt_tokens=0, completion_tokens=0, estimated_cost=0.0)
            
        except Exception as e:
            telemetry.record_failure(str(e))
            raise AIError(f"Unexpected AI streaming error: {str(e)}")
