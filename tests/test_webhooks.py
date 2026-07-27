"""
Tests for paypal_webhooks module.
"""

import json

import pytest
import requests
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
        """Test that API errors raise HTTPError."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks",
            json={"error": "unauthorized"},
            status=401,
        )

        from paypal_webhooks import list_webhooks

        with pytest.raises(requests.exceptions.HTTPError):
            list_webhooks()


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
        """Test that webhook creation failure raises HTTPError."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks",
            json={"error": "invalid_url"},
            status=400,
        )

        from paypal_webhooks import create_webhook

        with pytest.raises(requests.exceptions.HTTPError):
            create_webhook("invalid-url", ["PAYMENT.SALE.COMPLETED"])


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
        """Test that deleting non-existent webhook raises HTTPError."""
        responses.add(
            responses.DELETE,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks/WH-INVALID",
            json={"error": "not_found"},
            status=404,
        )

        from paypal_webhooks import delete_webhook

        with pytest.raises(requests.exceptions.HTTPError):
            delete_webhook("WH-INVALID")


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


class TestParseEventSelection:
    """Tests for interactive webhook event selection parsing."""

    event_types = [
        "PAYMENT.SALE.COMPLETED",
        "PAYMENT.SALE.REFUNDED",
        "BILLING.SUBSCRIPTION.CREATED",
        "CUSTOMER.DISPUTE.CREATED",
        "CUSTOMER.DISPUTE.RESOLVED",
    ]

    def test_parses_numbers_ranges_and_removes_duplicates(self):
        """Resolve mixed selections in the order entered."""
        from paypal_webhooks import parse_event_selection

        result = parse_event_selection("3,1-2,3", self.event_types)

        assert result == [
            "BILLING.SUBSCRIPTION.CREATED",
            "PAYMENT.SALE.COMPLETED",
            "PAYMENT.SALE.REFUNDED",
        ]

    @pytest.mark.parametrize("selection", ["all", "*"])
    def test_selects_all_events(self, selection):
        """Support convenient aliases for selecting every event."""
        from paypal_webhooks import parse_event_selection

        assert parse_event_selection(selection, self.event_types) == self.event_types

    @pytest.mark.parametrize(
        ("selection", "message"),
        [
            ("", "enter at least one"),
            ("two", "not an event number"),
            ("4-2", "must start with the lower number"),
            ("1,6", "outside 1-5"),
        ],
    )
    def test_rejects_invalid_selections(self, selection, message):
        """Explain invalid input so interactive users can correct it."""
        from paypal_webhooks import parse_event_selection

        with pytest.raises(ValueError, match=message):
            parse_event_selection(selection, self.event_types)


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

    @responses.activate
    def test_cli_create_prompts_for_event_selection(
        self, mock_env_vars, mock_auth, cli_runner
    ):
        """Create a webhook from numbered and ranged interactive choices."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks-event-types",
            json=SAMPLE_WEBHOOK_EVENT_TYPES,
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks",
            json=SAMPLE_WEBHOOK,
            status=201,
        )

        from paypal_webhooks import cli

        result = cli_runner.invoke(
            cli,
            ["create", "--url", "https://example.com/webhook"],
            input="1,3\ny\n",
        )

        assert result.exit_code == 0
        assert "1. PAYMENT.SALE.COMPLETED" in result.output
        assert "A sale completes" in result.output
        assert "3. BILLING.SUBSCRIPTION.CREATED" in result.output
        assert "Webhook created successfully." in result.output
        request_body = json.loads(responses.calls[-1].request.body)
        assert request_body["event_types"] == [
            {"name": "PAYMENT.SALE.COMPLETED"},
            {"name": "BILLING.SUBSCRIPTION.CREATED"},
        ]

    @responses.activate
    def test_cli_create_accepts_repeated_event_options(
        self, mock_env_vars, mock_auth, cli_runner
    ):
        """Preserve the non-interactive repeated -e workflow."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks",
            json=SAMPLE_WEBHOOK,
            status=201,
        )

        from paypal_webhooks import cli

        result = cli_runner.invoke(
            cli,
            [
                "create",
                "--url",
                "https://example.com/webhook",
                "-e",
                "PAYMENT.SALE.COMPLETED",
                "-e",
                "PAYMENT.SALE.REFUNDED",
            ],
        )

        assert result.exit_code == 0
        assert "Webhook created successfully." in result.output
        request_body = json.loads(responses.calls[-1].request.body)
        assert request_body["event_types"] == [
            {"name": "PAYMENT.SALE.COMPLETED"},
            {"name": "PAYMENT.SALE.REFUNDED"},
        ]

    @responses.activate
    def test_cli_create_reprompts_after_invalid_selection(
        self, mock_env_vars, mock_auth, cli_runner
    ):
        """Keep prompting until the user supplies a valid selection."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks-event-types",
            json=SAMPLE_WEBHOOK_EVENT_TYPES,
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks",
            json=SAMPLE_WEBHOOK,
            status=201,
        )

        from paypal_webhooks import cli

        result = cli_runner.invoke(
            cli,
            ["create", "--url", "https://example.com/webhook", "--interactive"],
            input="99\n2\ny\n",
        )

        assert result.exit_code == 0
        assert "Invalid selection: event number 99 is outside 1-3." in result.output
        assert "PAYMENT.SALE.REFUNDED" in result.output
        assert "Webhook created successfully." in result.output

    def test_cli_create_rejects_conflicting_selection_modes(self, cli_runner):
        """Keep scripted and interactive selection modes unambiguous."""
        from paypal_webhooks import cli

        result = cli_runner.invoke(
            cli,
            [
                "create",
                "--url",
                "https://example.com/webhook",
                "--events",
                "PAYMENT.SALE.COMPLETED",
                "--interactive",
            ],
        )

        assert result.exit_code == 2
        assert "Use only one of --events, --all-events, or --interactive." in result.output

    @responses.activate
    def test_cli_list_error_shows_error_output(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI list command shows error output on API failure."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks",
            json={"error": "unauthorized"},
            status=401,
        )

        from paypal_webhooks import cli

        result = cli_runner.invoke(cli, ["list"])
        assert "Error" in result.output

    @responses.activate
    def test_cli_delete_error_shows_error_output(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI delete command shows error output on API failure."""
        responses.add(
            responses.DELETE,
            f"{SANDBOX_API_BASE}/v1/notifications/webhooks/WH-INVALID",
            json={"error": "not_found"},
            status=404,
        )

        from paypal_webhooks import cli

        result = cli_runner.invoke(cli, ["delete", "WH-INVALID"])
        assert "Error" in result.output
