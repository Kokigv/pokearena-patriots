"""Adaptadores de proveedores de identidad (puerto ``IdentityProvider``).

- ``GoogleIdentityProvider`` valida el ID token de Google (OIDC) con PyJWT: firma con las
  llaves públicas de Google, emisor, audiencia (el Client ID de PokéArena) y expiración.
- ``TestIdentityProvider`` es el mecanismo de usuarios de prueba (US 118). Solo se conecta
  fuera de producción y produce cuentas marcadas como de prueba.
"""

from typing import Any, Protocol

import jwt

from pokearena.identity.domain.errors import InvalidProviderToken, ProviderUnavailable
from pokearena.identity.domain.player import ExternalIdentity

GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"


class SigningKeySource(Protocol):
    """Obtiene la llave pública que firmó un JWT (en producción, ``jwt.PyJWKClient``)."""

    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class GoogleIdentityProvider:
    name = "google"

    def __init__(self, client_id: str | None, keys: SigningKeySource) -> None:
        self._client_id = client_id
        self._keys = keys

    def verify(self, credential: str) -> ExternalIdentity:
        if not self._client_id:
            raise ProviderUnavailable(
                "Google",
                "El inicio de sesión con Google no está configurado en este ambiente "
                "(falta GOOGLE_CLIENT_ID).",
            )
        if not credential or credential.count(".") != 2:
            raise InvalidProviderToken("no tiene el formato de un ID token")
        try:
            key = self._keys.get_signing_key_from_jwt(credential)
        except jwt.PyJWKClientConnectionError as exc:
            raise ProviderUnavailable("Google") from exc
        except (jwt.PyJWKClientError, jwt.DecodeError) as exc:
            raise InvalidProviderToken("no fue firmado por Google") from exc
        try:
            claims = jwt.decode(
                credential,
                key.key if hasattr(key, "key") else key,
                algorithms=["RS256"],
                audience=self._client_id,
                options={"require": ["iss", "sub", "aud", "exp", "iat"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise InvalidProviderToken("expiró") from exc
        except jwt.InvalidAudienceError as exc:
            raise InvalidProviderToken("fue emitido para otra aplicación") from exc
        except jwt.InvalidSignatureError as exc:
            raise InvalidProviderToken("la firma no es válida") from exc
        except jwt.InvalidTokenError as exc:
            raise InvalidProviderToken("no se pudo validar") from exc
        if claims.get("iss") not in GOOGLE_ISSUERS:
            raise InvalidProviderToken("no fue emitido por Google")
        email = claims.get("email") if claims.get("email_verified", False) else None
        return ExternalIdentity(
            provider=self.name,
            subject=str(claims["sub"]),
            email=email,
            display_name=claims.get("name"),
        )


class TestIdentityProvider:
    """Usuarios de prueba: el "token" es el nombre del usuario. Nunca existe en producción."""

    __test__ = False  # evita que pytest la confunda con una clase de pruebas
    name = "test"

    def verify(self, credential: str) -> ExternalIdentity:
        return ExternalIdentity(
            provider=self.name,
            subject=credential,
            email=None,
            display_name=credential,
            is_test=True,
        )
