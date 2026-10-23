"""Credenciales de acceso como JWT firmados con HS256 (biblioteca, no framework: RES-01)."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from pokearena.identity.application.authentication import IssuedToken
from pokearena.shared.errors import NotAuthenticated, TokenExpired

_ALGORITHM = "HS256"


class JwtTokenCodec:
    def __init__(self, secret: str, issuer: str, ttl_minutes: int) -> None:
        self._secret = secret
        self._issuer = issuer
        self._ttl = timedelta(minutes=ttl_minutes)

    def issue(self, subject: str) -> IssuedToken:
        now = datetime.now(UTC)
        claims = {
            "sub": subject,
            "iss": self._issuer,
            "iat": now,
            "exp": now + self._ttl,
            "jti": str(uuid.uuid4()),
        }
        token = jwt.encode(claims, self._secret, algorithm=_ALGORITHM)
        return IssuedToken(access_token=token, expires_in=int(self._ttl.total_seconds()))

    def subject_of(self, token: str) -> str:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[_ALGORITHM],
                issuer=self._issuer,
                options={"require": ["sub", "exp", "iss"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpired() from exc
        except jwt.InvalidTokenError as exc:
            raise NotAuthenticated("La credencial de acceso no es válida.") from exc
        return str(claims["sub"])
