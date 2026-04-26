from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _get_user_or_ip(request: Request) -> str:
    """Rate limit key: user ID from JWT cookie if present, otherwise client IP."""
    token = request.cookies.get("access_token")
    if token:
        try:
            from jose import jwt
            from app.config import settings
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            return f"user:{payload['sub']}"
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug("Rate limiter JWT decode failed, falling back to IP: %s", e)
    return get_remote_address(request)


limiter = Limiter(key_func=_get_user_or_ip)
