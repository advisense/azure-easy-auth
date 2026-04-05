"""Microsoft Graph API integration for azure-easy-auth.

Opt-in module that uses the access token from Easy Auth headers to fetch
additional user information from the Microsoft Graph API.

Requires the ``graph`` extra::

    pip install azure-easy-auth[graph]

Usage::

    from azure_easy_auth import from_headers
    from azure_easy_auth.graph import get_access_token, fetch_profile, fetch_photo

    user = from_headers(request.headers)
    token = get_access_token(request.headers)
    if token:
        profile = fetch_profile(token)
        photo = fetch_photo(token)  # bytes or None
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import httpx

_HEADER_ACCESS_TOKEN = "X-MS-TOKEN-AAD-ACCESS-TOKEN"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


@dataclass(frozen=True)
class GraphProfile:
    """User profile from Microsoft Graph ``/me`` endpoint."""

    id: str | None = None
    """Azure AD object ID."""

    display_name: str | None = None
    """Full display name."""

    given_name: str | None = None
    """First name."""

    surname: str | None = None
    """Last name."""

    email: str | None = None
    """Primary email address (``mail`` field)."""

    user_principal_name: str | None = None
    """User principal name (typically ``user@domain``)."""

    job_title: str | None = None
    """Job title."""

    department: str | None = None
    """Department."""

    office_location: str | None = None
    """Office location."""

    company_name: str | None = None
    """Company name."""

    mobile_phone: str | None = None
    """Mobile phone number."""

    business_phones: list[str] = field(default_factory=list)
    """Business phone numbers."""

    raw: dict[str, Any] = field(default_factory=dict, repr=False)
    """Full raw JSON response from Graph, for any fields not mapped above."""


def _parse_profile(data: dict[str, Any]) -> GraphProfile:
    """Build a GraphProfile from a Graph API JSON response."""
    return GraphProfile(
        id=data.get("id"),
        display_name=data.get("displayName"),
        given_name=data.get("givenName"),
        surname=data.get("surname"),
        email=data.get("mail"),
        user_principal_name=data.get("userPrincipalName"),
        job_title=data.get("jobTitle"),
        department=data.get("department"),
        office_location=data.get("officeLocation"),
        company_name=data.get("companyName"),
        mobile_phone=data.get("mobilePhone"),
        business_phones=data.get("businessPhones") or [],
        raw=data,
    )


def get_access_token(headers: Mapping[str, str]) -> str | None:
    """Extract the AAD access token from Easy Auth headers.

    Returns ``None`` if the token store header is not present.  Make sure
    ``isTokenStoreEnabled`` is ``true`` in your App Service auth settings.
    """
    normalised = {k.upper(): v for k, v in headers.items()}
    return normalised.get(_HEADER_ACCESS_TOKEN.upper())


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _graph_get(
    path: str, token: str, *, client: httpx.Client | None = None,
) -> httpx.Response:
    """GET a Graph API endpoint, reusing *client* when provided."""
    c = client or httpx
    return c.get(f"{_GRAPH_BASE}{path}", headers=_auth_headers(token))


def fetch_profile(
    token: str, *, client: httpx.Client | None = None,
) -> GraphProfile:
    """Fetch the authenticated user's profile from Microsoft Graph.

    Pass an :class:`httpx.Client` to reuse connections across calls.
    Raises :class:`httpx.HTTPStatusError` on non-2xx responses.
    """
    resp = _graph_get("/me", token, client=client)
    resp.raise_for_status()
    return _parse_profile(resp.json())


def fetch_photo(
    token: str, *, client: httpx.Client | None = None,
) -> bytes | None:
    """Fetch the authenticated user's profile photo.

    Returns the raw image bytes (JPEG), or ``None`` if no photo is set.
    Pass an :class:`httpx.Client` to reuse connections across calls.
    """
    resp = _graph_get("/me/photo/$value", token, client=client)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.content


def fetch_manager(
    token: str, *, client: httpx.Client | None = None,
) -> GraphProfile | None:
    """Fetch the authenticated user's manager profile.

    Returns ``None`` if the user has no manager set in Azure AD.
    Pass an :class:`httpx.Client` to reuse connections across calls.
    """
    resp = _graph_get("/me/manager", token, client=client)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return _parse_profile(resp.json())
