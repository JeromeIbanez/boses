from fastapi import Response

from app.config import settings


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = settings.use_secure_cookies
    domain = ".temujintechnologies.com" if secure else None

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        domain=domain,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        domain=domain,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",  # only sent to auth endpoints
    )


def clear_auth_cookies(response: Response) -> None:
    secure = settings.use_secure_cookies
    domain = ".temujintechnologies.com" if secure else None

    response.delete_cookie("access_token", domain=domain)
    response.delete_cookie("refresh_token", path="/api/v1/auth", domain=domain)
