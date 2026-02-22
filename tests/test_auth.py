"""Tests for azure_easy_auth."""
import base64
import json

import pytest

from azure_easy_auth import Claim, EasyAuthUser, from_headers, is_authenticated


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_principal(claims: list[dict]) -> str:
    """Encode a principal payload the same way App Service does."""
    payload = {
        "auth_typ": "aad",
        "claims": claims,
        "name_typ": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        "role_typ": "http://schemas.microsoft.com/ws/2008/06/identity/claims/role",
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


AAD_CLAIMS = [
    {"typ": "aud", "val": "api://my-app"},
    {"typ": "iss", "val": "https://login.microsoftonline.com/tenant-id/v2.0"},
    {"typ": "name", "val": "Jane Doe"},
    {"typ": "oid", "val": "aaaa-bbbb-cccc"},
    {"typ": "preferred_username", "val": "jane@example.com"},
    {"typ": "roles", "val": "Reader"},
    {"typ": "roles", "val": "Writer"},
    {"typ": "groups", "val": "group-1"},
]

FULL_HEADERS = {
    "X-MS-CLIENT-PRINCIPAL-NAME": "Jane Doe",
    "X-MS-CLIENT-PRINCIPAL-ID": "aaaa-bbbb-cccc",
    "X-MS-CLIENT-PRINCIPAL-IDP": "aad",
    "X-MS-CLIENT-PRINCIPAL": _make_principal(AAD_CLAIMS),
}


# ---------------------------------------------------------------------------
# is_authenticated
# ---------------------------------------------------------------------------

class TestIsAuthenticated:
    def test_authenticated_when_headers_present(self):
        assert is_authenticated(FULL_HEADERS) is True

    def test_not_authenticated_when_no_headers(self):
        assert is_authenticated({}) is False

    def test_authenticated_with_only_name_header(self):
        assert is_authenticated({"X-MS-CLIENT-PRINCIPAL-NAME": "Bob"}) is True

    def test_authenticated_with_only_id_header(self):
        assert is_authenticated({"X-MS-CLIENT-PRINCIPAL-ID": "some-id"}) is True


# ---------------------------------------------------------------------------
# from_headers — basic fields
# ---------------------------------------------------------------------------

class TestFromHeaders:
    def test_name(self):
        user = from_headers(FULL_HEADERS)
        assert user.name == "Jane Doe"

    def test_principal_id(self):
        user = from_headers(FULL_HEADERS)
        assert user.principal_id == "aaaa-bbbb-cccc"

    def test_provider(self):
        user = from_headers(FULL_HEADERS)
        assert user.provider == "aad"

    def test_unauthenticated_user(self):
        user = from_headers({})
        assert user.is_authenticated is False
        assert user.name is None
        assert user.principal_id is None
        assert user.provider is None
        assert user.claims == []

    def test_header_names_are_case_insensitive(self):
        lowercased = {k.lower(): v for k, v in FULL_HEADERS.items()}
        user = from_headers(lowercased)
        assert user.name == "Jane Doe"
        assert user.provider == "aad"


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------

class TestClaims:
    def setup_method(self):
        self.user = from_headers(FULL_HEADERS)

    def test_claims_are_decoded(self):
        assert len(self.user.claims) == len(AAD_CLAIMS)

    def test_claim_types(self):
        types = {c.typ for c in self.user.claims}
        assert "oid" in types
        assert "preferred_username" in types

    def test_get_claim_single(self):
        assert self.user.get_claim("preferred_username") == "jane@example.com"

    def test_get_claim_missing_returns_none(self):
        assert self.user.get_claim("nonexistent") is None

    def test_get_claims_multi_value(self):
        assert self.user.get_claims("roles") == ["Reader", "Writer"]

    def test_get_claims_missing_returns_empty_list(self):
        assert self.user.get_claims("nonexistent") == []


# ---------------------------------------------------------------------------
# Convenience properties
# ---------------------------------------------------------------------------

class TestConvenienceProperties:
    def setup_method(self):
        self.user = from_headers(FULL_HEADERS)

    def test_email(self):
        assert self.user.email == "jane@example.com"

    def test_object_id(self):
        assert self.user.object_id == "aaaa-bbbb-cccc"

    def test_roles(self):
        assert self.user.roles == ["Reader", "Writer"]

    def test_groups(self):
        assert self.user.groups == ["group-1"]

    def test_email_falls_back_to_uri_claim(self):
        uri = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
        claims = [{"typ": uri, "val": "fallback@example.com"}]
        user = from_headers({
            "X-MS-CLIENT-PRINCIPAL-NAME": "Fallback User",
            "X-MS-CLIENT-PRINCIPAL": _make_principal(claims),
        })
        assert user.email == "fallback@example.com"

    def test_object_id_falls_back_to_uri_claim(self):
        uri = "http://schemas.microsoft.com/identity/claims/objectidentifier"
        claims = [{"typ": uri, "val": "uri-oid-value"}]
        user = from_headers({
            "X-MS-CLIENT-PRINCIPAL-NAME": "OID User",
            "X-MS-CLIENT-PRINCIPAL": _make_principal(claims),
        })
        assert user.object_id == "uri-oid-value"

    def test_roles_empty_when_no_claims(self):
        user = from_headers({"X-MS-CLIENT-PRINCIPAL-NAME": "No Roles"})
        assert user.roles == []

    def test_groups_empty_when_no_claims(self):
        user = from_headers({"X-MS-CLIENT-PRINCIPAL-NAME": "No Groups"})
        assert user.groups == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_malformed_principal_header_ignored(self):
        user = from_headers({
            "X-MS-CLIENT-PRINCIPAL-NAME": "Bob",
            "X-MS-CLIENT-PRINCIPAL": "!!!not-base64!!!",
        })
        assert user.name == "Bob"
        assert user.claims == []

    def test_principal_without_claims_key(self):
        payload = base64.b64encode(json.dumps({"auth_typ": "aad"}).encode()).decode()
        user = from_headers({
            "X-MS-CLIENT-PRINCIPAL-NAME": "Bob",
            "X-MS-CLIENT-PRINCIPAL": payload,
        })
        assert user.claims == []

    def test_claims_missing_typ_or_val_skipped(self):
        claims = [
            {"typ": "good", "val": "value"},
            {"typ": "missing-val"},
            {"val": "missing-typ"},
        ]
        principal = _make_principal(claims)
        user = from_headers({"X-MS-CLIENT-PRINCIPAL": principal})
        assert len(user.claims) == 1
        assert user.claims[0] == Claim(typ="good", val="value")
