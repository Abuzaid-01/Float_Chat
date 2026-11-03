"""
Request rate limiting for the endpoints that cost money or database time.

Every question runs an LLM call and one or more queries against the hosted
database.  A sliding-window limit per client address keeps one script, or one
stuck retry loop, from exhausting the LLM quota or the connection pool.

In-memory and per-process: enough for a single API instance.  Behind several
instances or a proxy, move this to the proxy or a shared store.
"""

import os
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

WINDOW_SECONDS = 60
# Paths that trigger the pipeline (LLM + database).
LIMITED_PREFIXES = (
    "/api/v1/chat",
    "/api/v1/query",
    "/api/v1/batch-query",
    "/api/v1/export",
    "/api/v1/analytics",
)


def _limit_per_minute() -> int:
    try:
        return int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
    except ValueError:
        return 30


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_per_minute: int = None):
        super().__init__(app)
        self.limit = _limit_per_minute() if limit_per_minute is None else limit_per_minute
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        if self.limit <= 0 or request.method == "OPTIONS" or not request.url.path.startswith(LIMITED_PREFIXES):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        now = time.time()
        with self._lock:
            hits = self._hits[client]
            while hits and now - hits[0] > WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = max(1, int(WINDOW_SECONDS - (now - hits[0])) + 1)
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"Too many requests. Try again in {retry_after} seconds."},
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)
            # Forget clients that have gone quiet so the table cannot grow forever.
            if len(self._hits) > 5000:
                for key in [key for key, value in self._hits.items() if not value]:
                    del self._hits[key]

        return await call_next(request)
