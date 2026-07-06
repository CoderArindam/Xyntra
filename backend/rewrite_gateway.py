import sys

with open('app/ai/gateway/ai_gateway.py', 'r') as f:
    content = f.read()

new_execute_prompt = """    def execute_prompt(
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
        self._check_feature_flags(org_ai_enabled, user_has_permission)

        with Span("LLM Call", "AIGateway") as span:
            span.metadata["provider"] = self.provider_name
            span.metadata["model"] = self.model_name
            span.metadata["workflow_id"] = workflow_id
            
            def do_call():
                response = self.provider.generate(
                    messages=messages,
                    temperature=settings.AI_TEMPERATURE,
                    max_tokens=settings.AI_MAX_TOKENS,
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
                                
                            parsed_json = json.loads(clean_content.strip())
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
            return policy.execute_sync(
                func=do_call,
                request_id=request_id,
                span_id=span.span_id,
                parent_span_id=span.parent_span_id,
                on_parsing_error=on_parsing_error
            )"""

# I need to add `content` property to ParsingError in `exceptions.py`
old_execute_prompt = content[content.find("    def execute_prompt("):content.find("    def stream_prompt(")]
new_content = content.replace(old_execute_prompt, new_execute_prompt + "\n\n")

with open('app/ai/gateway/ai_gateway.py', 'w') as f:
    f.write(new_content)
