import base64
import hashlib
import hmac
import logging
import secrets
import time
import uuid
from collections.abc import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings


SESSION_COOKIE_NAME = "me1ody_session"
SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60
_LOCAL_SESSION_SECRET = secrets.token_bytes(32)
_logger = logging.getLogger(__name__)


def _is_hosted_environment() -> bool:
    return settings.app_env not in {"local", "development", "test", "docker"}


def _encode_signature(payload: str, secret: bytes) -> str:
    digest = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def create_session_token(user_id: str, secret: bytes, now: int | None = None) -> str:
    expires_at = (now if now is not None else int(time.time())) + SESSION_MAX_AGE_SECONDS
    payload = f"v1.{user_id}.{expires_at}"
    return f"{payload}.{_encode_signature(payload, secret)}"


def verify_session_token(token: str, secret: bytes, now: int | None = None) -> str | None:
    try:
        version, user_id, expires_at_text, signature = token.split(".")
        uuid.UUID(user_id)
        expires_at = int(expires_at_text)
    except (ValueError, AttributeError):
        return None

    if version != "v1" or expires_at <= (now if now is not None else int(time.time())):
        return None

    payload = f"{version}.{user_id}.{expires_at}"
    expected = _encode_signature(payload, secret)
    return user_id if hmac.compare_digest(signature, expected) else None


def _configured_secret() -> bytes:
    configured = settings.session_secret.strip()
    if configured:
        secret = configured.encode("utf-8")
        if len(secret) < 32:
            raise RuntimeError("SESSION_SECRET must contain at least 32 bytes")
        return secret
    if _is_hosted_environment():
        raise RuntimeError("SESSION_SECRET is required outside local development")
    _logger.warning("SESSION_SECRET is unset; anonymous sessions will reset when the server restarts")
    return _LOCAL_SESSION_SECRET


class AnonymousSessionMiddleware(BaseHTTPMiddleware):
    """Assign each browser a signed, HttpOnly anonymous identity."""

    def __init__(self, app):
        super().__init__(app)
        self.secret = _configured_secret()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        token = request.cookies.get(SESSION_COOKIE_NAME, "")
        user_id = verify_session_token(token, self.secret)
        should_set_cookie = user_id is None
        if user_id is None:
            user_id = str(uuid.uuid4())

        request.state.user_id = user_id
        response = await call_next(request)

        if should_set_cookie and request.method != "OPTIONS":
            secure = _is_hosted_environment()
            response.set_cookie(
                SESSION_COOKIE_NAME,
                create_session_token(user_id, self.secret),
                max_age=SESSION_MAX_AGE_SECONDS,
                path="/",
                secure=secure,
                httponly=True,
                samesite="none" if secure else "lax",
            )
        return response


def get_user_id(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    return user_id if isinstance(user_id, str) else "anonymous"
