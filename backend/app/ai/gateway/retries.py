import time
import asyncio
from typing import Type, List, Callable, Any, Awaitable
from pydantic import BaseModel
from app.ai.exceptions import AIError, ProviderError, ParsingError
from app.ai.telemetry.events import EventType
from app.ai.telemetry.bus import telemetry_bus
from app.ai.telemetry.context import TraceContext

class RetryPolicy(BaseModel):
    max_retries: int = 3
    base_backoff_sec: float = 1.0
    max_backoff_sec: float = 10.0
    retryable_exceptions: List[Type[Exception]] = [ProviderError, ParsingError]
    
    def _calculate_backoff(self, attempt: int) -> float:
        backoff = self.base_backoff_sec * (2 ** (attempt - 1))
        return min(backoff, self.max_backoff_sec)

    async def execute_async(
        self,
        func: Callable[..., Any],
        request_id: str,
        span_id: str,
        parent_span_id: str,
        on_parsing_error: Callable[[ParsingError], None] = None,
        *args,
        **kwargs
    ) -> Any:
        retries = 0
        while retries <= self.max_retries:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if any(isinstance(e, ex_cls) for ex_cls in self.retryable_exceptions):
                    if isinstance(e, ProviderError):
                        # Treat 400 Bad Request / 401 / 403 / 404 / 429 as non-retryable
                        non_retryable_codes = ["400", "401", "403", "404", "429"]
                        if not getattr(e, 'is_retryable', True) or any(code in str(e) for code in non_retryable_codes):
                            raise e
                            
                    if retries < self.max_retries:
                        retries += 1
                        telemetry_bus.publish(
                            event_type=EventType.RETRY_OCCURRED,
                            request_id=request_id,
                            execution_id=TraceContext.get_execution_id(),
                            span_id=span_id,
                            parent_span_id=parent_span_id,
                            metadata={"reason": f"{e.__class__.__name__}: {str(e)}", "attempt": retries}
                        )
                        TraceContext.increment_metric("total_retries")
                        
                        if isinstance(e, ParsingError):
                            if retries > 1:
                                raise e # only retry parsing errors once
                            if on_parsing_error:
                                on_parsing_error(e)
                            # Do not back off for parsing errors, retry immediately with corrected prompt
                            continue
                        else:
                            await asyncio.sleep(self._calculate_backoff(retries))
                            continue
                raise e
