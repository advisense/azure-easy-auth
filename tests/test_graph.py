"""Tests for azure_easy_auth.graph module."""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from azure_easy_auth.graph import (
    GraphProfile,
    fetch_manager,
    fetch_photo,
    fetch_profile,
    get_access_token,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

FAKE_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.fake"

GRAPH_PROFILE_JSON = {
    "id": "aaaa-bbbb-cccc",
    "displayName": "Jane Doe",
    "givenName": "Jane",
    "surname": "Doe",
    "mail": "jane@example.com",
    "userPrincipalName": "jane@example.com",
    "jobTitle": "Engineer",
    "department": "Platform",
    "officeLocation": "Building 1",
    "companyName": "Contoso",
    "mobilePhone": "+1234567890",
    "businessPhones": ["+0987654321"],
}

MANAGER_JSON = {
    "id": "dddd-eeee-ffff",
    "displayName": "Bob Manager",
    "givenName": "Bob",
    "surname": "Manager",
    "mail": "bob@example.com",
    "userPrincipalName": "bob@example.com",
    "jobTitle": "Director",
    "department": "Platform",
    "officeLocation": None,
    "companyName": "Contoso",
    "mobilePhone": None,
    "businessPhones": [],
}


def _mock_response(status_code=200, json_data=None, content=None):
    """Build a fake httpx.Response."""
    resp = httpx.Response(
        status_code=status_code,
        json=json_data,
        content=content,
        request=httpx.Request("GET", "https://graph.microsoft.com/v1.0/me"),
    )
    return resp


# ---------------------------------------------------------------------------
# get_access_token
# ---------------------------------------------------------------------------

class TestGetAccessToken:
    def test_extracts_token(self):
        headers = {"X-MS-TOKEN-AAD-ACCESS-TOKEN": FAKE_TOKEN}
        assert get_access_token(headers) == FAKE_TOKEN

    def test_case_insensitive(self):
        headers = {"x-ms-token-aad-access-token": FAKE_TOKEN}
        assert get_access_token(headers) == FAKE_TOKEN

    def test_returns_none_when_missing(self):
        assert get_access_token({}) is None


# ---------------------------------------------------------------------------
# fetch_profile
# ---------------------------------------------------------------------------

class TestFetchProfile:
    @patch("azure_easy_auth.graph.httpx.get")
    def test_returns_profile(self, mock_get):
        mock_get.return_value = _mock_response(json_data=GRAPH_PROFILE_JSON)

        profile = fetch_profile(FAKE_TOKEN)

        assert profile.display_name == "Jane Doe"
        assert profile.given_name == "Jane"
        assert profile.surname == "Doe"
        assert profile.email == "jane@example.com"
        assert profile.job_title == "Engineer"
        assert profile.department == "Platform"
        assert profile.office_location == "Building 1"
        assert profile.company_name == "Contoso"
        assert profile.mobile_phone == "+1234567890"
        assert profile.business_phones == ["+0987654321"]
        assert profile.id == "aaaa-bbbb-cccc"

    @patch("azure_easy_auth.graph.httpx.get")
    def test_sends_bearer_token(self, mock_get):
        mock_get.return_value = _mock_response(json_data=GRAPH_PROFILE_JSON)

        fetch_profile(FAKE_TOKEN)

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["headers"]["Authorization"] == f"Bearer {FAKE_TOKEN}"

    @patch("azure_easy_auth.graph.httpx.get")
    def test_raises_on_error(self, mock_get):
        mock_get.return_value = _mock_response(status_code=401)

        with pytest.raises(httpx.HTTPStatusError):
            fetch_profile(FAKE_TOKEN)

    @patch("azure_easy_auth.graph.httpx.get")
    def test_raw_contains_full_response(self, mock_get):
        mock_get.return_value = _mock_response(json_data=GRAPH_PROFILE_JSON)

        profile = fetch_profile(FAKE_TOKEN)

        assert profile.raw == GRAPH_PROFILE_JSON

    @patch("azure_easy_auth.graph.httpx.get")
    def test_handles_missing_fields(self, mock_get):
        mock_get.return_value = _mock_response(json_data={"displayName": "Minimal"})

        profile = fetch_profile(FAKE_TOKEN)

        assert profile.display_name == "Minimal"
        assert profile.email is None
        assert profile.business_phones == []


# ---------------------------------------------------------------------------
# fetch_photo
# ---------------------------------------------------------------------------

class TestFetchPhoto:
    @patch("azure_easy_auth.graph.httpx.get")
    def test_returns_photo_bytes(self, mock_get):
        photo_bytes = b"\xff\xd8\xff\xe0fake-jpeg-data"
        mock_get.return_value = _mock_response(content=photo_bytes)

        result = fetch_photo(FAKE_TOKEN)

        assert result == photo_bytes

    @patch("azure_easy_auth.graph.httpx.get")
    def test_returns_none_when_no_photo(self, mock_get):
        mock_get.return_value = _mock_response(status_code=404)

        assert fetch_photo(FAKE_TOKEN) is None

    @patch("azure_easy_auth.graph.httpx.get")
    def test_raises_on_other_error(self, mock_get):
        mock_get.return_value = _mock_response(status_code=403)

        with pytest.raises(httpx.HTTPStatusError):
            fetch_photo(FAKE_TOKEN)


# ---------------------------------------------------------------------------
# fetch_manager
# ---------------------------------------------------------------------------

class TestFetchManager:
    @patch("azure_easy_auth.graph.httpx.get")
    def test_returns_manager_profile(self, mock_get):
        mock_get.return_value = _mock_response(json_data=MANAGER_JSON)

        manager = fetch_manager(FAKE_TOKEN)

        assert manager is not None
        assert manager.display_name == "Bob Manager"
        assert manager.email == "bob@example.com"
        assert manager.job_title == "Director"

    @patch("azure_easy_auth.graph.httpx.get")
    def test_returns_none_when_no_manager(self, mock_get):
        mock_get.return_value = _mock_response(status_code=404)

        assert fetch_manager(FAKE_TOKEN) is None

    @patch("azure_easy_auth.graph.httpx.get")
    def test_raises_on_other_error(self, mock_get):
        mock_get.return_value = _mock_response(status_code=500)

        with pytest.raises(httpx.HTTPStatusError):
            fetch_manager(FAKE_TOKEN)


# ---------------------------------------------------------------------------
# Client reuse
# ---------------------------------------------------------------------------

class TestClientReuse:
    def test_fetch_profile_uses_provided_client(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _mock_response(json_data=GRAPH_PROFILE_JSON)

        profile = fetch_profile(FAKE_TOKEN, client=mock_client)

        mock_client.get.assert_called_once()
        assert profile.display_name == "Jane Doe"

    def test_fetch_photo_uses_provided_client(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _mock_response(content=b"photo-data")

        result = fetch_photo(FAKE_TOKEN, client=mock_client)

        mock_client.get.assert_called_once()
        assert result == b"photo-data"

    def test_fetch_manager_uses_provided_client(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _mock_response(json_data=MANAGER_JSON)

        manager = fetch_manager(FAKE_TOKEN, client=mock_client)

        mock_client.get.assert_called_once()
        assert manager is not None
        assert manager.display_name == "Bob Manager"
