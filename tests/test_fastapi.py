"""Tests for the FastAPI integration."""
import base64
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from azure_easy_auth import EasyAuthUser
from azure_easy_auth.fastapi import AuthenticatedUser, CurrentUser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_principal(claims: list[dict]) -> str:
    payload = {"auth_typ": "aad", "claims": claims}
    return base64.b64encode(json.dumps(payload).encode()).decode()


AUTH_HEADERS = {
    "X-MS-CLIENT-PRINCIPAL-NAME": "Jane Doe",
    "X-MS-CLIENT-PRINCIPAL-ID": "aaaa-bbbb-cccc",
    "X-MS-CLIENT-PRINCIPAL-IDP": "aad",
    "X-MS-CLIENT-PRINCIPAL": _make_principal([
        {"typ": "preferred_username", "val": "jane@example.com"},
        {"typ": "roles", "val": "Reader"},
    ]),
}


# ---------------------------------------------------------------------------
# Test app
# ---------------------------------------------------------------------------

app = FastAPI()


@app.get("/me")
def me(user: AuthenticatedUser):
    return {"name": user.name, "email": user.email, "roles": user.roles}


@app.get("/public")
def public(user: CurrentUser):
    return {"authenticated": user.is_authenticated, "name": user.name}


client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# AuthenticatedUser
# ---------------------------------------------------------------------------

class TestAuthenticatedUser:
    def test_returns_user_when_authenticated(self):
        resp = client.get("/me", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Jane Doe"
        assert data["email"] == "jane@example.com"
        assert data["roles"] == ["Reader"]

    def test_raises_401_when_no_headers(self):
        resp = client.get("/me")
        assert resp.status_code == 401

    def test_401_detail_message(self):
        resp = client.get("/me")
        assert resp.json()["detail"] == "Not authenticated"


# ---------------------------------------------------------------------------
# CurrentUser
# ---------------------------------------------------------------------------

class TestCurrentUser:
    def test_returns_authenticated_user(self):
        resp = client.get("/public", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["authenticated"] is True
        assert resp.json()["name"] == "Jane Doe"

    def test_returns_unauthenticated_user_without_raising(self):
        resp = client.get("/public")
        assert resp.status_code == 200
        assert resp.json()["authenticated"] is False
        assert resp.json()["name"] is None
