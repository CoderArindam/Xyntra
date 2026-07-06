import sys

with open('app/services/ai_service.py', 'r') as f:
    content = f.read()

# We will construct a new chat_stream method.
new_chat_stream = """    async def chat_stream(self, request: AIChatRequest, current_user: dict, request_id: str) -> AsyncGenerator[str, None]:
        from app.ai.telemetry.context import TraceContext
        from app.ai.telemetry.tracer import RequestTracer
        from app.ai.orchestration.errors import ErrorMessageFactory
        from app.ai.orchestration.state_machine import ExecutionStateMachine
        from app.ai.orchestration.idempotency import idempotency_store
        from app.ai.orchestration.timeouts import timeout_policy
        from app.ai.exceptions import ExecutionTimeoutError, UserCancellationError, FailureCategory
        
        tracer = RequestTracer(
            request_id=request_id,
            user_id=str(current_user.get("id")),
            organization_id=str(current_user.get("organization_id"))
        )
        tracer.start()
        
        # Idempotency check
        idemp_key = f"{request.conversation_id}_{request_id}"
        if not idempotency_store.acquire(idemp_key):
            error_msg = ErrorMessageFactory._templates[FailureCategory.VALIDATION_ERROR]
            yield f"data: {json.dumps({'v': '1.0', 'type': 'error', 'error': error_msg, 'details': 'Duplicate request.'})}\\n\\n"
            tracer.end()
            return
            
        try:
            exec_context = ExecutionContext(
                current_user=current_user,
                conversation_id=request.conversation_id,
                request_id=request_id,
                organization_id=str(current_user.get("organization_id")),
                idempotency_key=idemp_key,
                current_state=ExecutionStatus.CREATED
            )
            exec_context.timeout_metadata = timeout_policy.model_dump()
            
            # Re-assign the generated execution ID from tracer to exec_context
            exec_context.execution_id = tracer.execution_id
            
            user_input = request.messages[-1].content if request.messages else ""
            
            if request.confirmed_plan:
                plan = ExecutionPlan(**request.confirmed_plan)
                skip_confirmation = True
                intent = IntentType.WORKSPACE_ACTION
                ExecutionStateMachine.validate_transition(exec_context.current_state, ExecutionStatus.WAITING_FOR_CONFIRMATION)
                exec_context.current_state = ExecutionStatus.WAITING_FOR_CONFIRMATION
            else:
                router = IntentRouter(self.gateway)
                intent = await router.classify(
                    user_input=user_input, 
                    request_id=exec_context.request_id, 
                    organization_id=exec_context.organization_id, 
                    user_id=str(exec_context.current_user.get("id"))
                )
                
            if intent in [IntentType.CONVERSATIONAL, IntentType.KNOWLEDGE]:
                yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_start', 'execution_id': exec_context.execution_id})}\\n\\n"
                
                from app.ai.prompts.registry import PromptRegistry
                system_prompt = PromptRegistry.render_prompt(
                    agent_name="workspace_assistant",
                    prompt_name="chat",
                    context={"current_user": json.dumps(exec_context.current_user)},
                    version="v1"
                )
                
                chat_messages = [{"role": "system", "content": system_prompt}] + [m.model_dump() for m in request.messages]
                
                stream_gen = self.gateway.stream_prompt(
                    messages=chat_messages,
                    org_ai_enabled=True,
                    user_has_permission=True,
                    workflow_id="conversational",
                    request_id=exec_context.request_id,
                    organization_id=exec_context.organization_id,
                    user_id=str(exec_context.current_user.get("id"))
                )
                
                for chunk in stream_gen:
                    if chunk and "content" in chunk:
                        yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_chunk', 'content': chunk['content']})}\\n\\n"
                        await asyncio.sleep(0)
                        
                yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_end'})}\\n\\n"
                return
                
            # WORKSPACE_ACTION flow
            if not request.confirmed_plan:
                ExecutionStateMachine.validate_transition(exec_context.current_state, ExecutionStatus.PLANNING)
                exec_context.current_state = ExecutionStatus.PLANNING
                yield f"data: {json.dumps({'v': '1.0', 'type': 'planning_started', 'timestamp': 0})}\\n\\n"
                
                planner = Planner(self.gateway)
                try:
                    plan = await asyncio.wait_for(
                        planner.create_plan(user_input, exec_context, agent.available_tools),
                        timeout=timeout_policy.planner_timeout_sec
                    )
                except asyncio.TimeoutError:
                    raise ExecutionTimeoutError("Planning timed out", stage="PLANNING")
                
                yield f"data: {json.dumps({'v': '1.0', 'type': 'planning_completed', 'plan': plan.model_dump(), 'timestamp': 0})}\\n\\n"
                skip_confirmation = False
                
            ExecutionStateMachine.validate_transition(exec_context.current_state, ExecutionStatus.VALIDATING)
            exec_context.current_state = ExecutionStatus.VALIDATING
            PlanValidator.validate(plan, exec_context, agent.available_tools)
            
            ExecutionStateMachine.validate_transition(exec_context.current_state, ExecutionStatus.EXECUTING)
            exec_context.current_state = ExecutionStatus.EXECUTING
            executor = Executor(services, agent.available_tools)
            execution_result = None
            
            try:
                # Use asyncio.wait_for for overall execution timeout
                async def run_executor():
                    nonlocal execution_result
                    async for event_string in executor.execute(plan, exec_context, skip_confirmation):
                        try:
                            event_data = json.loads(event_string.replace('data: ', '').strip())
                            if event_data.get('type') == 'execution_result':
                                from app.ai.schemas.planning import ExecutionResult
                                execution_result = ExecutionResult(**event_data.get('result'))
                                continue
                        except:
                            pass
                        yield event_string
                        await asyncio.sleep(0)
                
                async for evt in run_executor(): # No explicit timeout here since Executor handles tool timeouts and is a generator
                    yield evt
            except asyncio.TimeoutError:
                raise ExecutionTimeoutError("Overall execution timed out", stage="EXECUTING")
                
            if execution_result:
                ExecutionStateMachine.validate_transition(exec_context.current_state, execution_result.status)
                exec_context.current_state = execution_result.status
                if execution_result.status in [ExecutionStatus.COMPLETED, ExecutionStatus.PARTIALLY_COMPLETED]:
                    composer = ResponseComposer(self.gateway)
                    async for event_string in composer.compose(execution_result, exec_context):
                        yield event_string
                        await asyncio.sleep(0)
                
        except asyncio.CancelledError:
            exec_context.is_cancelled = True
            exec_context.current_state = ExecutionStatus.CANCELLED
            tracer.end(Exception("Request was cancelled"))
            yield f"data: {json.dumps({'v': '1.0', 'type': 'execution_cancelled'})}\\n\\n"
            raise
        except Exception as e:
            from app.ai.orchestration.errors import ErrorMessageFactory
            user_msg = ErrorMessageFactory.get_user_message(e)
            exec_context.current_state = ExecutionStatus.FAILED
            tracer.end(e)
            logger.error(f"Error in chat_stream: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'v': '1.0', 'type': 'error', 'error': user_msg})}\\n\\n"
        finally:
            idempotency_store.release(idemp_key)
            try:
                tracer.end()
                from app.ai.telemetry.context import _request_state
                state = _request_state.get()
                if state:
                    llm_calls = state.get("total_llm_calls", 0)
                    if intent == IntentType.CONVERSATIONAL and llm_calls > 0:
                        logger.warning(f"[PERFORMANCE BUDGET OVERSHOOT] Greeting used {llm_calls} LLM calls. Request: {request_id}")
                    elif intent == IntentType.WORKSPACE_ACTION and llm_calls > 1:
                        logger.warning(f"[PERFORMANCE BUDGET OVERSHOOT] Workspace read used {llm_calls} LLM calls. Request: {request_id}")
            except Exception:
                pass"""

# Find chat_stream definition and replace it
start_idx = content.find("    async def chat_stream")
if start_idx != -1:
    end_idx = content.find("def wrap_service_instance", start_idx) # wait, wrap_service_instance is not in ai_service.py.
    # The class ends after finally block. Let's just find the end of chat_stream.
    # It's the last method in AIService.
    old_chat_stream = content[start_idx:]
    new_content = content.replace(old_chat_stream, new_chat_stream + "\n")
    
    with open('app/services/ai_service.py', 'w') as f:
        f.write(new_content)
else:
    print("chat_stream not found")
