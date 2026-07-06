from typing import Optional
import threading

class IdempotencyStore:
    """Interface for tracking active and completed executions to prevent duplicates."""
    def acquire(self, key: str) -> bool:
        """Returns True if the lock/key was successfully acquired, False if it exists."""
        raise NotImplementedError()
        
    def release(self, key: str) -> None:
        """Releases the lock/key."""
        raise NotImplementedError()

class InMemoryIdempotencyStore(IdempotencyStore):
    def __init__(self):
        self._active = set()
        self._lock = threading.Lock()
        
    def acquire(self, key: str) -> bool:
        with self._lock:
            if key in self._active:
                return False
            self._active.add(key)
            return True
            
    def release(self, key: str) -> None:
        with self._lock:
            self._active.discard(key)

# Singleton instance for now
idempotency_store = InMemoryIdempotencyStore()
