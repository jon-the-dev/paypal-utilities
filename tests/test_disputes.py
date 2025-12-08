"""
Tests for paypal_disputes module.
"""

import pytest
import responses
from click.testing import CliRunner

from conftest import (
    SAMPLE_DISPUTE,
    SAMPLE_DISPUTE_DETAILS,
    SAMPLE_DISPUTES_RESPONSE,
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


class TestGetDisputes:
    """Tests for get_disputes function."""

    @responses.activate
    def test_get_disputes_success(self, mock_env_vars, mock_auth):
        """Test successful dispute listing."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/customer/disputes",
            json=SAMPLE_DISPUTES_RESPONSE,
            status=200,
        )

        from paypal_disputes import get_disputes

        disputes = get_disputes()

        assert len(disputes) == 1
        assert disputes[0]["dispute_id"] == "PP-D-123456"
        assert disputes[0]["status"] == "OPEN"

    @responses.activate
    def test_get_disputes_with_status_filter(self, mock_env_vars, mock_auth):
        """Test dispute listing with status filter."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/customer/disputes",
            json=SAMPLE_DISPUTES_RESPONSE,
            status=200,
        )

        from paypal_disputes import get_disputes

        disputes = get_disputes(dispute_state="OPEN")

        # Verify status filter was passed
        assert "dispute_state=OPEN" in responses.calls[1].request.url

    @responses.activate
    def test_get_disputes_with_date_filter(self, mock_env_vars, mock_auth):
        """Test dispute listing with date filter."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/customer/disputes",
            json=SAMPLE_DISPUTES_RESPONSE,
            status=200,
        )

        from paypal_disputes import get_disputes

        disputes = get_disputes(start_date="2024-01-01T00:00:00Z")

        # Verify date filter was passed
        assert "start_time" in responses.calls[1].request.url

    @responses.activate
    def test_get_disputes_pagination(self, mock_env_vars, mock_auth):
        """Test dispute listing with pagination."""
        # First page
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/customer/disputes",
            json={
                "items": [SAMPLE_DISPUTE],
                "links": [{"rel": "next", "href": f"{SANDBOX_API_BASE}/v1/customer/disputes?page=2"}],
            },
            status=200,
        )
        # Second page
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/customer/disputes?page=2",
            json={
                "items": [{**SAMPLE_DISPUTE, "dispute_id": "PP-D-654321"}],
                "links": [],
            },
            status=200,
        )

        from paypal_disputes import get_disputes

        disputes = get_disputes()

        assert len(disputes) == 2

    @responses.activate
    def test_get_disputes_empty(self, mock_env_vars, mock_auth):
        """Test when no disputes found."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/customer/disputes",
            json={"items": [], "links": []},
            status=200,
        )

        from paypal_disputes import get_disputes

        disputes = get_disputes()
        assert disputes == []


class TestGetDisputeDetails:
    """Tests for get_dispute_details function."""

    @responses.activate
    def test_get_dispute_details_success(self, mock_env_vars, mock_auth):
        """Test successful dispute detail retrieval."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/customer/disputes/PP-D-123456",
            json=SAMPLE_DISPUTE_DETAILS,
            status=200,
        )

        from paypal_disputes import get_dispute_details

        dispute = get_dispute_details("PP-D-123456")

        assert dispute is not None
        assert dispute["dispute_id"] == "PP-D-123456"
        assert dispute["dispute_outcome"]["outcome_code"] == "RESOLVED_BUYER_FAVOUR"

    @responses.activate
    def test_get_dispute_details_not_found(self, mock_env_vars, mock_auth):
        """Test getting non-existent dispute."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/customer/disputes/PP-D-INVALID",
            json={"error": "not_found"},
            status=404,
        )

        from paypal_disputes import get_dispute_details

        dispute = get_dispute_details("PP-D-INVALID")
        assert dispute is None


class TestFormatDispute:
    """Tests for format_dispute function."""

    def test_format_dispute_complete(self, mock_env_vars):
        """Test formatting a complete dispute."""
        from paypal_disputes import format_dispute

        formatted = format_dispute(SAMPLE_DISPUTE)

        assert formatted["id"] == "PP-D-123456"
        assert formatted["status"] == "OPEN"
        assert formatted["reason"] == "MERCHANDISE_OR_SERVICE_NOT_RECEIVED"
        assert "50.00" in formatted["amount"]


class TestDisputesCLI:
    """Tests for disputes CLI commands."""

    @responses.activate
    def test_cli_list_command(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI list command."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/customer/disputes",
            json=SAMPLE_DISPUTES_RESPONSE,
            status=200,
        )

        from paypal_disputes import cli

        result = cli_runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "PP-D-123456" in result.output

    @responses.activate
    def test_cli_list_with_status_filter(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI list command with status filter."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/customer/disputes",
            json=SAMPLE_DISPUTES_RESPONSE,
            status=200,
        )

        from paypal_disputes import cli

        result = cli_runner.invoke(cli, ["list", "--status", "OPEN"])
        assert result.exit_code == 0

    @responses.activate
    def test_cli_show_command(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI show command."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/customer/disputes/PP-D-123456",
            json=SAMPLE_DISPUTE_DETAILS,
            status=200,
        )

        from paypal_disputes import cli

        result = cli_runner.invoke(cli, ["show", "PP-D-123456"])
        assert result.exit_code == 0
        assert "PP-D-123456" in result.output
        assert "MERCHANDISE_OR_SERVICE_NOT_RECEIVED" in result.output

    @responses.activate
    def test_cli_summary_command(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI summary command."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/customer/disputes",
            json=SAMPLE_DISPUTES_RESPONSE,
            status=200,
        )

        from paypal_disputes import cli

        result = cli_runner.invoke(cli, ["summary", "--days", "90"])
        assert result.exit_code == 0
        assert "Dispute Summary" in result.output

    @responses.activate
    def test_cli_summary_with_action_required(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI summary shows action required warning."""
        action_required_response = {
            "items": [
                {**SAMPLE_DISPUTE, "status": "WAITING_FOR_SELLER_RESPONSE"},
            ],
            "links": [],
        }
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/customer/disputes",
            json=action_required_response,
            status=200,
        )

        from paypal_disputes import cli

        result = cli_runner.invoke(cli, ["summary"])
        assert result.exit_code == 0
        assert "require your response" in result.output

    @responses.activate
    def test_cli_list_no_disputes(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI list when no disputes found."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/customer/disputes",
            json={"items": [], "links": []},
            status=200,
        )

        from paypal_disputes import cli

        result = cli_runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "No disputes found" in result.output
