import os
import logging
from datetime import datetime
from typing import Dict, List
from fastapi import HTTPException

logger = logging.getLogger(__name__)

_RATE_LIMIT_STORE: Dict[int, List[datetime]] = {}
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", 500))
RATE_LIMIT_WINDOW = 60  # seconds


def check_rate_limit(user_id: int):
    now = datetime.utcnow()
    timestamps = _RATE_LIMIT_STORE.get(user_id, [])
    timestamps = [ts for ts in timestamps if (now - ts).total_seconds() < RATE_LIMIT_WINDOW]

    if len(timestamps) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(status_code=429, detail="AI request rate limit exceeded. Please try again later.")

    timestamps.append(now)
    _RATE_LIMIT_STORE[user_id] = timestamps
