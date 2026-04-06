"""
Tests for paypal_balance module.
"""

import pytest
import requests
import responses
from click.testing import CliRunner

from conftest import (
    SAMPLE_BALANCE,
    SAMPLE_BALANCES_RESPONSE,
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


class TestGetBalances:
    """Tests for get_balances function."""

    @responses.activate
    def test_get_balances_success(self, mock_env_vars, mock_auth):
        """Test successful balance retrieval."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/balances",
            json=SAMPLE_BALANCES_RESPONSE,
            status=200,
        )

        from paypal_balance import get_balances

        balances = get_balances()

        assert len(balances) == 1
        assert balances[0]["currency"] == "USD"
        assert balances[0]["available_balance"]["value"] == "1000.00"

    @responses.activate
    def test_get_balances_with_date(self, mock_env_vars, mock_auth):
        """Test historical balance retrieval."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/balances",
            json=SAMPLE_BALANCES_RESPONSE,
            status=200,
        )

        from paypal_balance import get_balances

        balances = get_balances(as_of_date="2024-01-15T23:59:59Z")

        # Verify date parameter was passed
        assert "as_of_time" in responses.calls[1].request.url

    @responses.activate
    def test_get_balances_multiple_currencies(self, mock_env_vars, mock_auth):
        """Test balance retrieval with multiple currencies."""
        multi_currency_response = {
            "balances": [
                SAMPLE_BALANCE,
                {
                    "currency": "EUR",
                    "available_balance": {"value": "500.00", "currency_code": "EUR"},
                    "total_balance": {"value": "500.00", "currency_code": "EUR"},
                },
            ],
        }
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/balances",
            json=multi_currency_response,
            status=200,
        )

        from paypal_balance import get_balances

        balances = get_balances()

        assert len(balances) == 2
        currencies = [b["currency"] for b in balances]
        assert "USD" in currencies
        assert "EUR" in currencies

    @responses.activate
    def test_get_balances_empty(self, mock_env_vars, mock_auth):
        """Test when no balances available."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/balances",
            json={"balances": []},
            status=200,
        )

        from paypal_balance import get_balances

        balances = get_balances()
        assert balances == []

    @responses.activate
    def test_get_balances_api_error(self, mock_env_vars, mock_auth):
        """Test that API errors raise HTTPError."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/balances",
            json={"error": "unauthorized"},
            status=401,
        )

        from paypal_balance import get_balances

        with pytest.raises(requests.exceptions.HTTPError):
            get_balances()


class TestBalanceCLI:
    """Tests for balance CLI commands."""

    @responses.activate
    def test_cli_show_command(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI show command."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/balances",
            json=SAMPLE_BALANCES_RESPONSE,
            status=200,
        )

        from paypal_balance import cli

        result = cli_runner.invoke(cli, ["show"])
        assert result.exit_code == 0
        assert "USD" in result.output
        assert "1,000.00" in result.output or "1000.00" in result.output

    @responses.activate
    def test_cli_show_with_currency_filter(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI show command with currency filter."""
        multi_currency_response = {
            "balances": [
                SAMPLE_BALANCE,
                {
                    "currency": "EUR",
                    "available_balance": {"value": "500.00", "currency_code": "EUR"},
                },
            ],
        }
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/balances",
            json=multi_currency_response,
            status=200,
        )

        from paypal_balance import cli

        result = cli_runner.invoke(cli, ["show", "--currency", "USD"])
        assert result.exit_code == 0
        assert "USD" in result.output

    @responses.activate
    def test_cli_show_with_date(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI show command with historical date."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/balances",
            json=SAMPLE_BALANCES_RESPONSE,
            status=200,
        )

        from paypal_balance import cli

        result = cli_runner.invoke(cli, ["show", "--date", "2024-01-15"])
        assert result.exit_code == 0
        assert "2024-01-15" in result.output

    @responses.activate
    def test_cli_summary_command(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI summary command."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/balances",
            json=SAMPLE_BALANCES_RESPONSE,
            status=200,
        )

        from paypal_balance import cli

        result = cli_runner.invoke(cli, ["summary"])
        assert result.exit_code == 0
        assert "Balance Summary" in result.output

    @responses.activate
    def test_cli_show_no_balances(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI show when no balances available."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/balances",
            json={"balances": []},
            status=200,
        )

        from paypal_balance import cli

        result = cli_runner.invoke(cli, ["show"])
        assert result.exit_code == 0
        assert "No balance" in result.output

    @responses.activate
    def test_cli_show_error_shows_error_output(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI show command shows error output on API failure."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/balances",
            json={"error": "unauthorized"},
            status=401,
        )

        from paypal_balance import cli

        result = cli_runner.invoke(cli, ["show"])
        assert "Error" in result.output

    @responses.activate
    def test_cli_summary_error_shows_error_output(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI summary command shows error output on API failure."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/balances",
            json={"error": "unauthorized"},
            status=401,
        )

        from paypal_balance import cli

        result = cli_runner.invoke(cli, ["summary"])
        assert "Error" in result.output
