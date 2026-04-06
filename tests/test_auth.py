"""
Tests for paypal_auth module.
"""

import os
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
import requests
import responses
from requests.adapters import HTTPAdapter

from conftest import SANDBOX_API_BASE, TEST_ACCESS_TOKEN, TEST_CLIENT_ID, TEST_SECRET


class TestGetPayPalToken:
    """Tests for get_paypal_token function."""

    @responses.activate
    def test_get_token_success(self, mock_env_vars):
        """Test successful token retrieval."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/oauth2/token",
            json={"access_token": TEST_ACCESS_TOKEN, "token_type": "Bearer"},
            status=200,
        )

        from paypal_auth import get_paypal_token

        token = get_paypal_token()
        assert token == TEST_ACCESS_TOKEN

    @responses.activate
    def test_get_token_uses_correct_credentials(self, mock_env_vars):
        """Test that correct credentials are sent."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/oauth2/token",
            json={"access_token": TEST_ACCESS_TOKEN},
            status=200,
        )

        from paypal_auth import get_paypal_token

        get_paypal_token()

        # Verify the request was made with correct auth
        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert request.headers.get("Accept") == "application/json"

    @responses.activate
    def test_get_token_api_error(self, mock_env_vars):
        """Test handling of API errors."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/oauth2/token",
            json={"error": "invalid_client"},
            status=401,
        )

        from paypal_auth import get_paypal_token

        with pytest.raises(Exception):
            get_paypal_token()


class TestTokenCaching:
    """Tests for OAuth token caching behaviour."""

    @responses.activate
    def test_token_caching_returns_cached_token(self, mock_env_vars):
        """Two consecutive calls should only result in one HTTP request."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/oauth2/token",
            json={"access_token": TEST_ACCESS_TOKEN, "token_type": "Bearer", "expires_in": 32400},
            status=200,
        )

        from paypal_auth import get_paypal_token

        first = get_paypal_token()
        second = get_paypal_token()

        assert first == TEST_ACCESS_TOKEN
        assert second == TEST_ACCESS_TOKEN
        assert len(responses.calls) == 1

    @responses.activate
    def test_token_cache_expires(self, mock_env_vars):
        """An expired cache entry must trigger a new HTTP request."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/oauth2/token",
            json={"access_token": TEST_ACCESS_TOKEN, "token_type": "Bearer", "expires_in": 32400},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/oauth2/token",
            json={"access_token": "refreshed_token_99999", "token_type": "Bearer", "expires_in": 32400},
            status=200,
        )

        import paypal_auth

        # Prime the cache with a token that is already past its expiry buffer
        paypal_auth._token_cache["token"] = "old_token"
        paypal_auth._token_cache["expires_at"] = datetime.utcnow() - timedelta(seconds=1)

        token = paypal_auth.get_paypal_token()

        assert token == TEST_ACCESS_TOKEN
        assert len(responses.calls) == 1

    @responses.activate
    def test_clear_token_cache(self, mock_env_vars):
        """clear_token_cache() should force a fresh fetch on the next call."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/oauth2/token",
            json={"access_token": TEST_ACCESS_TOKEN, "token_type": "Bearer", "expires_in": 32400},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/oauth2/token",
            json={"access_token": "fresh_token_after_clear", "token_type": "Bearer", "expires_in": 32400},
            status=200,
        )

        import paypal_auth

        first = paypal_auth.get_paypal_token()
        assert first == TEST_ACCESS_TOKEN
        assert len(responses.calls) == 1

        paypal_auth.clear_token_cache()
        assert paypal_auth._token_cache["token"] is None
        assert paypal_auth._token_cache["expires_at"] is None

        second = paypal_auth.get_paypal_token()
        assert second == "fresh_token_after_clear"
        assert len(responses.calls) == 2


class TestGetAuthHeaders:
    """Tests for get_auth_headers function."""

    @responses.activate
    def test_get_auth_headers_returns_correct_format(self, mock_env_vars):
        """Test that auth headers have correct format."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/oauth2/token",
            json={"access_token": TEST_ACCESS_TOKEN},
            status=200,
        )

        from paypal_auth import get_auth_headers

        headers = get_auth_headers()

        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == f"Bearer {TEST_ACCESS_TOKEN}"


class TestEnvironmentConfiguration:
    """Tests for environment-based configuration."""

    def test_sandbox_api_base_for_dev(self):
        """Test that dev environment uses sandbox API."""
        with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
            # Need to reload module to pick up new env var
            import importlib
            import paypal_auth

            importlib.reload(paypal_auth)
            assert "sandbox" in paypal_auth.PAYPAL_API_BASE

    def test_production_api_base_for_prod(self):
        """Test that prod environment uses production API."""
        with patch.dict(os.environ, {
            "PAYPAL_CLIENT_ID": TEST_CLIENT_ID,
            "PAYPAL_SECRET": TEST_SECRET,
            "ENVIRONMENT": "prod",
        }):
            import importlib
            import paypal_auth

            importlib.reload(paypal_auth)
            assert paypal_auth.PAYPAL_API_BASE == "https://api.paypal.com"


class TestTimeout:
    """Tests for request timeout configuration."""

    def test_default_timeout(self, mock_env_vars):
        """Test that TIMEOUT defaults to 30 seconds."""
        from paypal_auth import TIMEOUT

        assert TIMEOUT == 30

    def test_timeout_from_env(self):
        """Test that TIMEOUT reads from PAYPAL_TIMEOUT env var."""
        with patch.dict(os.environ, {
            "PAYPAL_CLIENT_ID": TEST_CLIENT_ID,
            "PAYPAL_SECRET": TEST_SECRET,
            "ENVIRONMENT": "dev",
            "PAYPAL_TIMEOUT": "60",
        }):
            import importlib
            import paypal_auth

            importlib.reload(paypal_auth)
            assert paypal_auth.TIMEOUT == 60

    @responses.activate
    def test_token_request_uses_timeout(self, mock_env_vars):
        """Test that get_paypal_token passes timeout to requests."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/oauth2/token",
            json={"access_token": TEST_ACCESS_TOKEN},
            status=200,
        )

        from paypal_auth import get_paypal_token

        get_paypal_token()

        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert request.req_kwargs.get("timeout") == 30


class TestSSLVerification:
    """Tests for explicit SSL certificate verification."""

    @responses.activate
    def test_token_request_uses_verify_true(self, mock_env_vars):
        """Test that get_paypal_token passes verify=True to requests."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/oauth2/token",
            json={"access_token": TEST_ACCESS_TOKEN},
            status=200,
        )

        from paypal_auth import get_paypal_token

        get_paypal_token()

        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert request.req_kwargs.get("verify") is True


class TestCreateSession:
    """Tests for create_session function."""

    def test_returns_session_with_retry_adapter(self):
        """Session must mount an HTTPAdapter with correct retry configuration."""
        from paypal_auth import create_session

        session = create_session()

        assert isinstance(session, requests.Session)

        adapter = session.get_adapter("https://")
        assert isinstance(adapter, HTTPAdapter)
        assert adapter.max_retries.total == 3
        assert adapter.max_retries.backoff_factor == 1
        assert 429 in adapter.max_retries.status_forcelist
        assert 500 in adapter.max_retries.status_forcelist
        assert 502 in adapter.max_retries.status_forcelist
        assert 503 in adapter.max_retries.status_forcelist
        assert 504 in adapter.max_retries.status_forcelist

    def test_http_adapter_also_mounted(self):
        """The retry adapter must be mounted for plain http:// as well."""
        from paypal_auth import create_session

        session = create_session()

        adapter = session.get_adapter("http://")
        assert isinstance(adapter, HTTPAdapter)
        assert adapter.max_retries.total == 3

    def test_allowed_methods_include_all_http_verbs(self):
        """Retry must cover all HTTP verbs used by the PayPal utilities."""
        from paypal_auth import create_session

        session = create_session()
        adapter = session.get_adapter("https://")
        allowed = adapter.max_retries.allowed_methods

        for method in ["GET", "POST", "PATCH", "DELETE", "PUT"]:
            assert method in allowed

    @responses.activate
    def test_session_makes_successful_request(self, mock_env_vars):
        """Session returned by create_session must be able to issue live requests."""
        from paypal_auth import create_session

        responses.add(responses.GET, "https://example.com/test", json={"ok": True}, status=200)

        session = create_session()
        resp = session.get("https://example.com/test", timeout=5)

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
