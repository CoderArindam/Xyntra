from functools import wraps
import time
from .context import Span, TraceContext

def trace_service(service_name: str, method_name: str):
    """Decorator to wrap a service method with a telemetry Span."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with Span(method_name, service_name) as span:
                try:
                    result = await func(*args, **kwargs)
                    TraceContext.increment_metric("services_invoked")
                    return result
                except Exception as e:
                    span.metadata["error"] = str(e)
                    raise
                    
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with Span(method_name, service_name) as span:
                try:
                    result = func(*args, **kwargs)
                    TraceContext.increment_metric("services_invoked")
                    return result
                except Exception as e:
                    span.metadata["error"] = str(e)
                    raise
                    
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
        
    return decorator

