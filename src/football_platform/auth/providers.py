"""Authentication providers behind one interface (D032).

The API only needs to know *who* is calling: an `Identity` (issuer + stable subject). Logging in happens
at an external identity provider (Amazon Cognito or any OpenID Connect provider); this module verifies the
token it issued. Choose the provider with AUTH_PROVIDER:

- `disabled` (default): personal features (recruitment board) are off; the analytics stay public.
- `dev`: every request is the same local user. For a single-user local or private instance only.
- `oidc`: verify a bearer JWT (RS256) against the issuer's published keys. For Cognito:
  OIDC_ISSUER=https://cognito-idp.<region>.amazonaws.com/<user-pool-id>, OIDC_CLIENT_ID=<app client id>.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Protocol

import jwt

logger = logging.getLogger(__name__)

DEFAULT_SCOPES = "openid email profile"
CLOCK_SKEW_S = 30  # tolerated clock difference between this server and the identity provider
ALGORITHMS = ["RS256"]  # Cognito and most OIDC providers sign with RSA; never accept "none" or HMAC
TOKEN_USES = {"access", "id"}  # Cognito's token_use claim


@dataclass(frozen=True)
class Identity:
    issuer: str
    subject: str
    email: str | None = None
    name: str | None = None


class AuthenticationError(Exception):
    """The request carries no valid credentials (HTTP 401)."""


class AuthNotConfiguredError(Exception):
    """No identity provider is configured, so personal features are unavailable (HTTP 503)."""


class AuthProvider(Protocol):
    mode: str

    def authenticate(self, authorization: str | None) -> Identity:
        """Identity behind an Authorization header value; raises AuthenticationError."""
        ...

    def public_config(self) -> dict[str, Any]:
        """What the browser needs to start a login (never secrets)."""
        ...


class DisabledAuthProvider:
    mode = "disabled"

    def authenticate(self, authorization: str | None) -> Identity:
        raise AuthNotConfiguredError("Login is not configured on this server (AUTH_PROVIDER)")

    def public_config(self) -> dict[str, Any]:
        return {"mode": self.mode}


class DevAuthProvider:
    """One fixed local user, no credentials. Anyone who can reach the server acts as this user."""

    mode = "dev"
    IDENTITY = Identity(issuer="dev", subject="local-user", email=None, name="Local user")

    def authenticate(self, authorization: str | None) -> Identity:
        return self.IDENTITY

    def public_config(self) -> dict[str, Any]:
        return {"mode": self.mode}


def _http_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read())


class OidcAuthProvider:
    """Verifies RS256 JWTs from an OpenID Connect issuer (Cognito ID or access tokens)."""

    mode = "oidc"

    def __init__(self, issuer: str, client_id: str, scopes: str = DEFAULT_SCOPES,
                 fetch_json: Callable[[str], dict[str, Any]] = _http_json,
                 jwks_client: jwt.PyJWKClient | None = None) -> None:
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.scopes = scopes
        self._fetch_json = fetch_json
        self._jwks_client = jwks_client

    @cached_property
    def discovery(self) -> dict[str, Any]:
        """The issuer's OpenID configuration (endpoints and key set URL), fetched once."""
        document = self._fetch_json(f"{self.issuer}/.well-known/openid-configuration")
        if document.get("issuer", "").rstrip("/") != self.issuer:
            raise RuntimeError("OIDC discovery document does not match OIDC_ISSUER")
        return document

    @property
    def jwks_client(self) -> jwt.PyJWKClient:
        if self._jwks_client is None:  # PyJWKClient caches the keys and refetches on an unknown key id
            self._jwks_client = jwt.PyJWKClient(self.discovery["jwks_uri"])
        return self._jwks_client

    def authenticate(self, authorization: str | None) -> Identity:
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthenticationError("Missing bearer token")
        try:
            key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token, key.key, algorithms=ALGORITHMS, issuer=self.issuer, leeway=CLOCK_SKEW_S,
                options={"verify_aud": False, "require": ["exp", "iat", "iss", "sub"]},
            )
        except (jwt.PyJWTError, KeyError) as error:
            raise AuthenticationError(f"Invalid token: {error}") from None
        self._check_client(claims)
        return Identity(
            issuer=self.issuer, subject=claims["sub"], email=claims.get("email"),
            name=claims.get("name") or claims.get("cognito:username") or claims.get("username"),
        )

    def _check_client(self, claims: Mapping[str, Any]) -> None:
        """The token must be issued for this app: `aud` (ID tokens) or `client_id` (Cognito access tokens)."""
        audience = claims.get("aud")
        audiences = audience if isinstance(audience, list) else [audience]
        if self.client_id not in audiences and claims.get("client_id") != self.client_id:
            raise AuthenticationError("Token was issued for another client")
        if "token_use" in claims and claims["token_use"] not in TOKEN_USES:
            raise AuthenticationError("Unexpected token use")

    def public_config(self) -> dict[str, Any]:
        config: dict[str, Any] = {"mode": self.mode, "issuer": self.issuer, "client_id": self.client_id,
                                  "scopes": self.scopes}
        try:
            config["authorization_endpoint"] = self.discovery["authorization_endpoint"]
            config["token_endpoint"] = self.discovery["token_endpoint"]
            config["end_session_endpoint"] = self.discovery.get("end_session_endpoint")
        except (OSError, KeyError, RuntimeError, ValueError) as error:
            logger.warning("OIDC discovery failed: %s", error)
            config["error"] = "Identity provider unreachable"
        return config


def provider_from_env(env: Mapping[str, str] | None = None) -> AuthProvider:
    env = os.environ if env is None else env
    mode = env.get("AUTH_PROVIDER", "disabled").strip().lower() or "disabled"
    if mode == "disabled":
        return DisabledAuthProvider()
    if mode == "dev":
        logger.warning("AUTH_PROVIDER=dev: every visitor acts as the same local user. Never expose this publicly.")
        return DevAuthProvider()
    if mode == "oidc":
        issuer, client_id = env.get("OIDC_ISSUER", ""), env.get("OIDC_CLIENT_ID", "")
        if not issuer or not client_id:
            raise ValueError("AUTH_PROVIDER=oidc needs OIDC_ISSUER and OIDC_CLIENT_ID")
        return OidcAuthProvider(issuer, client_id, env.get("OIDC_SCOPES", DEFAULT_SCOPES))
    raise ValueError(f"Unknown AUTH_PROVIDER {mode!r} (disabled, dev or oidc)")
