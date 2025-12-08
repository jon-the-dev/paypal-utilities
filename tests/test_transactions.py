"""
Tests for paypal_transactions module.
"""

import csv
import os
import tempfile
from datetime import datetime, timedelta

import pytest
import responses
from click.testing import CliRunner

from conftest import (
    SAMPLE_TRANSACTION,
    SAMPLE_TRANSACTIONS_RESPONSE,
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


class TestGetTransactions:
    """Tests for get_transactions function."""

    @responses.activate
    def test_get_transactions_success(self, mock_env_vars, mock_auth):
        """Test successful transaction retrieval."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/transactions",
            json=SAMPLE_TRANSACTIONS_RESPONSE,
            status=200,
        )

        from paypal_transactions import get_transactions

        transactions = get_transactions(
            "2024-01-01T00:00:00Z",
            "2024-01-31T23:59:59Z",
        )

        assert len(transactions) == 1
        assert transactions[0]["transaction_info"]["transaction_id"] == "TXN-123456789"

    @responses.activate
    def test_get_transactions_with_status_filter(self, mock_env_vars, mock_auth):
        """Test transaction retrieval with status filter."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/transactions",
            json=SAMPLE_TRANSACTIONS_RESPONSE,
            status=200,
        )

        from paypal_transactions import get_transactions

        transactions = get_transactions(
            "2024-01-01T00:00:00Z",
            "2024-01-31T23:59:59Z",
            transaction_status="S",
        )

        # Verify status filter was passed
        assert "transaction_status=S" in responses.calls[1].request.url

    @responses.activate
    def test_get_transactions_pagination(self, mock_env_vars, mock_auth):
        """Test transaction retrieval with pagination."""
        # First page
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/transactions",
            json={
                "transaction_details": [SAMPLE_TRANSACTION],
                "total_pages": 2,
            },
            status=200,
        )
        # Second page
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/transactions",
            json={
                "transaction_details": [SAMPLE_TRANSACTION],
                "total_pages": 2,
            },
            status=200,
        )

        from paypal_transactions import get_transactions

        transactions = get_transactions(
            "2024-01-01T00:00:00Z",
            "2024-01-31T23:59:59Z",
        )

        assert len(transactions) == 2

    @responses.activate
    def test_get_transactions_empty(self, mock_env_vars, mock_auth):
        """Test when no transactions found."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/transactions",
            json={"transaction_details": [], "total_pages": 0},
            status=200,
        )

        from paypal_transactions import get_transactions

        transactions = get_transactions(
            "2024-01-01T00:00:00Z",
            "2024-01-31T23:59:59Z",
        )

        assert transactions == []


class TestFormatTransaction:
    """Tests for format_transaction function."""

    def test_format_transaction_complete(self, mock_env_vars):
        """Test formatting a complete transaction."""
        from paypal_transactions import format_transaction

        formatted = format_transaction(SAMPLE_TRANSACTION)

        assert formatted["id"] == "TXN-123456789"
        assert formatted["status"] == "S"
        assert "100.00" in formatted["amount"]
        assert "USD" in formatted["amount"]
        assert formatted["payer_email"] == "buyer@example.com"
        assert "John" in formatted["payer_name"]

    def test_format_transaction_minimal(self, mock_env_vars):
        """Test formatting a transaction with minimal data."""
        from paypal_transactions import format_transaction

        minimal_txn = {
            "transaction_info": {
                "transaction_id": "TXN-MIN",
            },
            "payer_info": {},
        }

        formatted = format_transaction(minimal_txn)
        assert formatted["id"] == "TXN-MIN"
        assert formatted["payer_email"] == "N/A"


class TestExportToCSV:
    """Tests for CSV export functionality."""

    def test_export_to_csv_success(self, mock_env_vars):
        """Test successful CSV export."""
        from paypal_transactions import export_to_csv

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = f.name

        try:
            export_to_csv([SAMPLE_TRANSACTION], output_path)

            # Verify file was created and has content
            assert os.path.exists(output_path)

            with open(output_path, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 1
                assert rows[0]["id"] == "TXN-123456789"
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_export_to_csv_empty(self, mock_env_vars):
        """Test export with no transactions."""
        from paypal_transactions import export_to_csv

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = f.name

        try:
            export_to_csv([], output_path)
            # File should not be created for empty data
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestTransactionsCLI:
    """Tests for transactions CLI commands."""

    @responses.activate
    def test_cli_list_command(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI list command."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/transactions",
            json=SAMPLE_TRANSACTIONS_RESPONSE,
            status=200,
        )

        from paypal_transactions import cli

        result = cli_runner.invoke(cli, ["list", "--days", "7"])
        assert result.exit_code == 0
        assert "TXN-123456789" in result.output

    @responses.activate
    def test_cli_list_with_date_range(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI list command with date range."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/transactions",
            json=SAMPLE_TRANSACTIONS_RESPONSE,
            status=200,
        )

        from paypal_transactions import cli

        result = cli_runner.invoke(cli, [
            "list",
            "--start", "2024-01-01",
            "--end", "2024-01-31",
        ])
        assert result.exit_code == 0

    @responses.activate
    def test_cli_summary_command(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI summary command."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/transactions",
            json=SAMPLE_TRANSACTIONS_RESPONSE,
            status=200,
        )

        from paypal_transactions import cli

        result = cli_runner.invoke(cli, ["summary", "--days", "30"])
        assert result.exit_code == 0
        assert "Transaction Summary" in result.output

    @responses.activate
    def test_cli_export_command(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI export command."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/reporting/transactions",
            json=SAMPLE_TRANSACTIONS_RESPONSE,
            status=200,
        )

        from paypal_transactions import cli

        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(cli, [
                "export",
                "--days", "7",
                "--output", "test_export.csv",
            ])
            assert result.exit_code == 0
            assert os.path.exists("test_export.csv")
