from functools import wraps
import time
from .context import Span, TraceContext

def trace_service(service_name: str, method_name: str):
    """
    Decorator to wrap a service method with a telemetry Span.
    """
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

def wrap_service_instance(service_instance, service_name: str):
    """
    Wraps an entire service instance dynamically, applying @trace_service 
    to all public methods. This prevents having to modify business logic files.
    """
    class WrappedService:
        def __init__(self):
            self._cache = {}
            
        def __getattr__(self, name):
            attr = getattr(service_instance, name)
            if callable(attr) and not name.startswith('_'):
                traced = trace_service(service_name, name)(attr)
                
                # Only cache read operations within the request scope
                if name.startswith("get_") or name.startswith("list_"):
                    from functools import wraps
                    import asyncio
                    
                    @wraps(attr)
                    async def memoized_async(*args, **kwargs):
                        key = f"{name}:{str(args)}:{str(kwargs)}"
                        if key in self._cache:
                            return self._cache[key]
                        res = await traced(*args, **kwargs)
                        self._cache[key] = res
                        return res
                        
                    @wraps(attr)
                    def memoized_sync(*args, **kwargs):
                        key = f"{name}:{str(args)}:{str(kwargs)}"
                        if key in self._cache:
                            return self._cache[key]
                        res = traced(*args, **kwargs)
                        self._cache[key] = res
                        return res
                        
                    if asyncio.iscoroutinefunction(attr):
                        return memoized_async
                    return memoized_sync
                    
                return traced
            return attr
    return WrappedService()
