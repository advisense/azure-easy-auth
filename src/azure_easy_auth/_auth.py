"""Core Azure Easy Auth header parsing."""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any, Mapping


# Header names injected by App Service authentication
_HEADER_PRINCIPAL = "X-MS-CLIENT-PRINCIPAL"
_HEADER_PRINCIPAL_NAME = "X-MS-CLIENT-PRINCIPAL-NAME"
_HEADER_PRINCIPAL_ID = "X-MS-CLIENT-PRINCIPAL-ID"
_HEADER_PRINCIPAL_IDP = "X-MS-CLIENT-PRINCIPAL-IDP"

# Well-known claim type URIs used by Azure AD
_CLAIM_EMAIL_URI = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
_CLAIM_OID_URI = "http://schemas.microsoft.com/identity/claims/objectidentifier"
_CLAIM_ROLES_URI = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"
_CLAIM_GROUPS_URI = "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups"
_CLAIM_NAME_URI = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"


@dataclass(frozen=True)
class Claim:
    """A single claim from the principal token."""

    typ: str
    val: str


@dataclass(frozen=True)
class EasyAuthUser:
    """
    Represents a user authenticated via Azure App Service Easy Auth.

    Populated from the X-MS-CLIENT-PRINCIPAL* headers injected by the
    App Service authentication module.
    """

    name: str | None
    """Display name from X-MS-CLIENT-PRINCIPAL-NAME."""

    principal_id: str | None
    """Object/subject ID from X-MS-CLIENT-PRINCIPAL-ID."""

    provider: str | None
    """Identity provider from X-MS-CLIENT-PRINCIPAL-IDP (e.g. 'aad')."""

    claims: list[Claim] = field(default_factory=list)
    """All claims decoded from X-MS-CLIENT-PRINCIPAL."""

    _claims_by_type: dict[str, list[str]] = field(
        default_factory=dict, repr=False, compare=False, hash=False
    )

    @property
    def is_authenticated(self) -> bool:
        """True when Easy Auth headers are present."""
        return self.name is not None or self.principal_id is not None

    def get_claim(self, typ: str) -> str | None:
        """Return the first value for a claim type, or None."""
        values = self._claims_by_type.get(typ)
        return values[0] if values else None

    def get_claims(self, typ: str) -> list[str]:
        """Return all values for a claim type."""
        return list(self._claims_by_type.get(typ, []))

    @property
    def email(self) -> str | None:
        """Email address claim (preferred_username or emailaddress)."""
        return self.get_claim("preferred_username") or self.get_claim(_CLAIM_EMAIL_URI)

    @property
    def object_id(self) -> str | None:
        """Azure AD object ID (oid or objectidentifier URI claim)."""
        return self.get_claim("oid") or self.get_claim(_CLAIM_OID_URI)

    @property
    def roles(self) -> list[str]:
        """App roles assigned to the user."""
        return self.get_claims("roles") or self.get_claims(_CLAIM_ROLES_URI)

    @property
    def groups(self) -> list[str]:
        """Group membership claims."""
        return self.get_claims("groups") or self.get_claims(_CLAIM_GROUPS_URI)


def _decode_principal(header_value: str) -> tuple[list[Claim], dict[str, list[str]]]:
    """Decode the base64-encoded X-MS-CLIENT-PRINCIPAL JSON payload."""
    try:
        # Standard base64 — pad if needed
        padded = header_value + "=" * (-len(header_value) % 4)
        payload: dict[str, Any] = json.loads(base64.b64decode(padded).decode("utf-8"))
    except Exception:
        return [], {}

    raw_claims: list[dict[str, str]] = payload.get("claims", [])
    claims = [Claim(typ=c["typ"], val=c["val"]) for c in raw_claims if "typ" in c and "val" in c]
    by_type: dict[str, list[str]] = {}
    for claim in claims:
        by_type.setdefault(claim.typ, []).append(claim.val)
    return claims, by_type


def from_headers(headers: Mapping[str, str]) -> EasyAuthUser:
    """
    Build an :class:`EasyAuthUser` from a request headers mapping.

    Works with any case-insensitive or case-sensitive header mapping
    (e.g. ``request.headers`` from Flask, Django, FastAPI, WSGI environ).

    If the Easy Auth headers are absent the returned user will have
    :attr:`EasyAuthUser.is_authenticated` == ``False``.
    """
    # Build a normalised lookup so callers don't need to worry about casing
    normalised = {k.upper(): v for k, v in headers.items()}

    name = normalised.get(_HEADER_PRINCIPAL_NAME.upper())
    principal_id = normalised.get(_HEADER_PRINCIPAL_ID.upper())
    provider = normalised.get(_HEADER_PRINCIPAL_IDP.upper())

    principal_header = normalised.get(_HEADER_PRINCIPAL.upper())
    if principal_header:
        claims, by_type = _decode_principal(principal_header)
    else:
        claims, by_type = [], {}

    return EasyAuthUser(
        name=name,
        principal_id=principal_id,
        provider=provider,
        claims=claims,
        _claims_by_type=by_type,
    )


def is_authenticated(headers: Mapping[str, str]) -> bool:
    """Return True if Easy Auth headers indicate an authenticated user."""
    return from_headers(headers).is_authenticated
