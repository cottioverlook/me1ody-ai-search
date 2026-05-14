from collections import defaultdict, deque
from time import monotonic

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings


PUBLIC_API_EXEMPT_PATHS = {"/api/health", "/api/ready"}


class PublicAccessMiddleware(BaseHTTPMiddleware):
    """Protect public test deployments with a shared token and light IP limits."""

    def __init__(self, app):
        super().__init__(app)
        self.minute_hits: dict[str, deque[float]] = defaultdict(deque)
        self.day_hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if not self._should_protect(request):
            return await call_next(request)

        if settings.public_test_token:
            supplied_token = request.headers.get("x-test-token", "")
            if supplied_token != settings.public_test_token:
                return JSONResponse(
                    {"detail": "Invalid or missing test token."},
                    status_code=401,
                )

        client_key = self._client_key(request)
        if self._rate_limited(client_key):
            return JSONResponse(
                {"detail": "Too many requests. Please try again later."},
                status_code=429,
                headers={"Retry-After": "60"},
            )

        return await call_next(request)

    def _should_protect(self, request: Request) -> bool:
        if request.method == "OPTIONS":
            return False
        if not settings.public_test_token and settings.app_env not in {"render", "production"}:
            return False
        return request.url.path.startswith("/api/") and request.url.path not in PUBLIC_API_EXEMPT_PATHS

    def _client_key(self, request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _rate_limited(self, client_key: str) -> bool:
        now = monotonic()
        minute_window = 60
        day_window = 24 * 60 * 60

        minute_hits = self.minute_hits[client_key]
        day_hits = self.day_hits[client_key]

        self._prune(minute_hits, now - minute_window)
        self._prune(day_hits, now - day_window)

        if settings.rate_limit_per_minute > 0 and len(minute_hits) >= settings.rate_limit_per_minute:
            return True
        if settings.rate_limit_per_day > 0 and len(day_hits) >= settings.rate_limit_per_day:
            return True

        minute_hits.append(now)
        day_hits.append(now)
        return False

    def _prune(self, hits: deque[float], minimum_allowed: float) -> None:
        while hits and hits[0] < minimum_allowed:
            hits.popleft()
