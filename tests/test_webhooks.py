"""
Tests for paypal_webhooks module.
"""

import pytest
import responses
from click.testing import CliRunner

from conftest import (
    SAMPLE_WEBHOOK,
    SAMPLE_WEBHOOK_EVENT_TYPES,
    SAMPLE_WEBHOOKS_RESPONSE,
    SANDBOX_API_BASE,
    TEST_ACCESS_TOKEN,
)


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing Click commands."""
    return CliRunner()


@pytest.fixture
def mock_auth():
    """Mock OAuth token endpoint."""
    responses.add(
        responses.POST,
        f"{SANDBOX_API_BASE}/v1/oauth2/token",
        json={"access_token": TEST_ACCESS_TOKEN},
        status=200,
    )


class TestListWebhooks:
    """Tests for list_webhooks function."""

    @responses.activate
    def test_list_webhooks_success(self, mock_env_vars, mock_auth):
        """Test successful webhook listing."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks",
            json=SAMPLE_WEBHOOKS_RESPONSE,
            status=200,
        )

        from paypal_webhooks import list_webhooks

        webhooks = list_webhooks()
        assert len(webhooks) == 1
        assert webhooks[0]["id"] == "WH-123456789"

    @responses.activate
    def test_list_webhooks_empty(self, mock_env_vars, mock_auth):
        """Test listing when no webhooks exist."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks",
            json={"webhooks": []},
            status=200,
        )

        from paypal_webhooks import list_webhooks

        webhooks = list_webhooks()
        assert webhooks == []

    @responses.activate
    def test_list_webhooks_api_error(self, mock_env_vars, mock_auth):
        """Test handling of API errors."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks",
            json={"error": "unauthorized"},
            status=401,
        )

        from paypal_webhooks import list_webhooks

        webhooks = list_webhooks()
        assert webhooks == []


class TestCreateWebhook:
    """Tests for create_webhook function."""

    @responses.activate
    def test_create_webhook_success(self, mock_env_vars, mock_auth):
        """Test successful webhook creation."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks",
            json=SAMPLE_WEBHOOK,
            status=201,
        )

        from paypal_webhooks import create_webhook

        result = create_webhook(
            "https://example.com/webhook",
            ["PAYMENT.SALE.COMPLETED"],
        )
        assert result is not None
        assert result["id"] == "WH-123456789"

    @responses.activate
    def test_create_webhook_with_multiple_events(self, mock_env_vars, mock_auth):
        """Test creating webhook with multiple event types."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks",
            json=SAMPLE_WEBHOOK,
            status=201,
        )

        from paypal_webhooks import create_webhook

        result = create_webhook(
            "https://example.com/webhook",
            ["PAYMENT.SALE.COMPLETED", "PAYMENT.SALE.REFUNDED"],
        )
        assert result is not None

        # Verify request payload
        request_body = responses.calls[1].request.body
        assert b"PAYMENT.SALE.COMPLETED" in request_body
        assert b"PAYMENT.SALE.REFUNDED" in request_body

    @responses.activate
    def test_create_webhook_failure(self, mock_env_vars, mock_auth):
        """Test webhook creation failure."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks",
            json={"error": "invalid_url"},
            status=400,
        )

        from paypal_webhooks import create_webhook

        result = create_webhook("invalid-url", ["PAYMENT.SALE.COMPLETED"])
        assert result is None


class TestDeleteWebhook:
    """Tests for delete_webhook function."""

    @responses.activate
    def test_delete_webhook_success(self, mock_env_vars, mock_auth):
        """Test successful webhook deletion."""
        responses.add(
            responses.DELETE,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks/WH-123456789",
            status=204,
        )

        from paypal_webhooks import delete_webhook

        result = delete_webhook("WH-123456789")
        assert result is True

    @responses.activate
    def test_delete_webhook_not_found(self, mock_env_vars, mock_auth):
        """Test deleting non-existent webhook."""
        responses.add(
            responses.DELETE,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks/WH-INVALID",
            json={"error": "not_found"},
            status=404,
        )

        from paypal_webhooks import delete_webhook

        result = delete_webhook("WH-INVALID")
        assert result is False


class TestGetWebhookEventTypes:
    """Tests for get_webhook_event_types function."""

    @responses.activate
    def test_get_event_types_success(self, mock_env_vars, mock_auth):
        """Test successful event types retrieval."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks-event-types",
            json=SAMPLE_WEBHOOK_EVENT_TYPES,
            status=200,
        )

        from paypal_webhooks import get_webhook_event_types

        event_types = get_webhook_event_types()
        assert len(event_types) == 3
        assert "PAYMENT.SALE.COMPLETED" in event_types


class TestWebhooksCLI:
    """Tests for webhook CLI commands."""

    @responses.activate
    def test_cli_list_command(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI list command."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks",
            json=SAMPLE_WEBHOOKS_RESPONSE,
            status=200,
        )

        from paypal_webhooks import cli

        result = cli_runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "WH-123456789" in result.output

    @responses.activate
    def test_cli_events_command(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI events command."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks-event-types",
            json=SAMPLE_WEBHOOK_EVENT_TYPES,
            status=200,
        )

        from paypal_webhooks import cli

        result = cli_runner.invoke(cli, ["events"])
        assert result.exit_code == 0
        assert "PAYMENT.SALE.COMPLETED" in result.output
