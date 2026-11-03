from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import urlparse

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError

from app.schemas import Identity

JWT_ALGORITHM = "RS256"
JWT_REQUIRED_CLAIMS = ("sub", "role", "iss", "aud", "exp")
JWKS_TIMEOUT_SECONDS = 3
AUTHORIZATION_SCHEME = "bearer"
LOCAL_JWKS_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


@lru_cache(maxsize=8)
def jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, timeout=JWKS_TIMEOUT_SECONDS)


def get_identity(authorization: str = Header(default="")) -> Identity:
    token = _extract_bearer_token(authorization)
    issuer = os.getenv("JWT_ISSUER")
    audience = os.getenv("JWT_AUDIENCE")
    jwks_url = os.getenv("JWT_JWKS_URL")
    if not issuer or not audience or not jwks_url or not _is_secure_jwks_url(jwks_url):
        raise HTTPException(status_code=503, detail="Authentication is not configured")

    try:
        signing_key = jwks_client(jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[JWT_ALGORITHM],
            issuer=issuer,
            audience=audience,
            options={"require": list(JWT_REQUIRED_CLAIMS)},
        )
        return Identity(username=claims["sub"], role=claims["role"])
    except PyJWKClientConnectionError as error:
        raise HTTPException(
            status_code=503,
            detail="Authentication service is unavailable",
        ) from error
    except (PyJWTError, KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=401, detail="Invalid token") from error


def _extract_bearer_token(authorization: str) -> str:
    scheme, separator, credentials = authorization.partition(" ")
    if (
        not separator
        or scheme.lower() != AUTHORIZATION_SCHEME
        or not credentials.strip()
    ):
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.strip()


def _is_secure_jwks_url(jwks_url: str) -> bool:
    try:
        parsed_url = urlparse(jwks_url)
    except ValueError:
        return False

    if parsed_url.scheme == "https":
        return (
            bool(parsed_url.hostname)
            and not parsed_url.username
            and not parsed_url.password
        )
    return (
        parsed_url.scheme == "http"
        and parsed_url.hostname in LOCAL_JWKS_HOSTS
        and not parsed_url.username
        and not parsed_url.password
    )
