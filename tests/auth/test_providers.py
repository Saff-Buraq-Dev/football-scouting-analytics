import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from football_platform.auth.providers import (
    AuthenticationError, AuthNotConfiguredError, DevAuthProvider, DisabledAuthProvider, OidcAuthProvider,
    provider_from_env,
)

ISSUER = "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_TEST"
CLIENT = "client-123"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class StubJwks:
    """Stands in for PyJWKClient: one known key id."""

    def get_signing_key_from_jwt(self, token):
        if jwt.get_unverified_header(token).get("kid") != "k1":
            raise jwt.PyJWKClientError("Unknown key id")
        return jwt.PyJWK.from_dict({**jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key(), as_dict=True),
                                    "kid": "k1", "alg": "RS256"})


def token(key=KEY, kid="k1", algorithm="RS256", **overrides):
    now = int(time.time())
    claims = {"iss": ISSUER, "sub": "user-1", "aud": CLIENT, "iat": now, "exp": now + 300,
              "token_use": "id", "email": "scout@example.com", "cognito:username": "scout"}
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm=algorithm, headers={"kid": kid})


@pytest.fixture
def provider():
    return OidcAuthProvider(ISSUER, CLIENT, fetch_json=lambda url: {}, jwks_client=StubJwks())


def test_valid_id_token_gives_the_identity(provider):
    identity = provider.authenticate(f"Bearer {token()}")
    assert (identity.issuer, identity.subject, identity.email, identity.name) == (ISSUER, "user-1", "scout@example.com", "scout")


def test_cognito_access_token_is_matched_on_client_id(provider):
    access = token(aud=None, client_id=CLIENT, token_use="access", email=None)
    assert provider.authenticate(f"Bearer {access}").subject == "user-1"


@pytest.mark.parametrize("bad", [
    {"aud": "another-client"},
    {"iss": "https://evil.example.com"},
    {"exp": int(time.time()) - 3600},
    {"sub": None},
    {"token_use": "refresh"},
])
def test_invalid_claims_are_rejected(provider, bad):
    with pytest.raises(AuthenticationError):
        provider.authenticate(f"Bearer {token(**bad)}")


def test_signature_from_another_key_is_rejected(provider):
    with pytest.raises(AuthenticationError):
        provider.authenticate(f"Bearer {token(key=OTHER_KEY)}")


def test_unknown_key_id_and_unsigned_tokens_are_rejected(provider):
    with pytest.raises(AuthenticationError):
        provider.authenticate(f"Bearer {token(kid='k2')}")
    unsigned = jwt.encode({"iss": ISSUER, "sub": "x", "aud": CLIENT}, None, algorithm="none", headers={"kid": "k1"})
    with pytest.raises(AuthenticationError):
        provider.authenticate(f"Bearer {unsigned}")


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer"])
def test_missing_or_malformed_header_is_rejected(provider, header):
    with pytest.raises(AuthenticationError):
        provider.authenticate(header)


def test_discovery_must_match_the_configured_issuer():
    provider = OidcAuthProvider(ISSUER, CLIENT, fetch_json=lambda url: {"issuer": "https://other"})
    assert provider.public_config()["error"] == "Identity provider unreachable"


def test_public_config_exposes_endpoints_not_secrets():
    discovery = {"issuer": ISSUER, "jwks_uri": f"{ISSUER}/.well-known/jwks.json",
                 "authorization_endpoint": "https://auth.example.com/oauth2/authorize",
                 "token_endpoint": "https://auth.example.com/oauth2/token"}
    config = OidcAuthProvider(ISSUER, CLIENT, fetch_json=lambda url: discovery).public_config()
    assert config == {"mode": "oidc", "issuer": ISSUER, "client_id": CLIENT, "scopes": "openid email profile",
                      "authorization_endpoint": discovery["authorization_endpoint"],
                      "token_endpoint": discovery["token_endpoint"], "end_session_endpoint": None}


def test_provider_from_env():
    assert isinstance(provider_from_env({}), DisabledAuthProvider)
    assert isinstance(provider_from_env({"AUTH_PROVIDER": "dev"}), DevAuthProvider)
    oidc = provider_from_env({"AUTH_PROVIDER": "oidc", "OIDC_ISSUER": ISSUER + "/", "OIDC_CLIENT_ID": CLIENT})
    assert isinstance(oidc, OidcAuthProvider) and oidc.issuer == ISSUER
    with pytest.raises(ValueError):
        provider_from_env({"AUTH_PROVIDER": "oidc"})
    with pytest.raises(ValueError):
        provider_from_env({"AUTH_PROVIDER": "magic"})


def test_disabled_provider_refuses_with_a_configuration_error():
    with pytest.raises(AuthNotConfiguredError):
        DisabledAuthProvider().authenticate("Bearer x")
