"""
Shared pytest fixtures for PayPal utilities tests.
"""

import importlib
import os
import sys
import tempfile
from unittest.mock import patch

import pytest
import responses

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test constants
SANDBOX_API_BASE = "https://api.sandbox.paypal.com"
TEST_CLIENT_ID = "test_client_id"
TEST_SECRET = "test_secret"
TEST_ACCESS_TOKEN = "test_access_token_12345"


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables for all tests and reload modules."""
    with patch.dict(os.environ, {
        "PAYPAL_CLIENT_ID": TEST_CLIENT_ID,
        "PAYPAL_SECRET": TEST_SECRET,
        "ENVIRONMENT": "dev",
    }):
        # Reload paypal_auth to pick up mocked environment variables
        import paypal_auth
        importlib.reload(paypal_auth)
        yield


@pytest.fixture
def mock_oauth_token():
    """Mock the OAuth token endpoint."""
    responses.add(
        responses.POST,
        f"{SANDBOX_API_BASE}/v1/oauth2/token",
        json={"access_token": TEST_ACCESS_TOKEN, "token_type": "Bearer", "expires_in": 32400},
        status=200,
    )


@pytest.fixture
def temp_csv_file():
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        yield f.name
    # Cleanup
    if os.path.exists(f.name):
        os.unlink(f.name)


# Sample API response data

SAMPLE_WEBHOOK = {
    "id": "WH-123456789",
    "url": "https://example.com/webhook",
    "event_types": [
        {"name": "PAYMENT.SALE.COMPLETED", "description": "Payment completed"},
        {"name": "PAYMENT.SALE.REFUNDED", "description": "Payment refunded"},
    ],
    "links": [],
}

SAMPLE_WEBHOOKS_RESPONSE = {
    "webhooks": [SAMPLE_WEBHOOK],
}

SAMPLE_WEBHOOK_EVENT_TYPES = {
    "event_types": [
        {"name": "PAYMENT.SALE.COMPLETED", "description": "A sale completes"},
        {"name": "PAYMENT.SALE.REFUNDED", "description": "A sale is refunded"},
        {"name": "BILLING.SUBSCRIPTION.CREATED", "description": "Subscription created"},
    ],
}

SAMPLE_PRODUCT = {
    "id": "PROD-123456789",
    "name": "Test Product",
    "description": "A test product",
    "type": "SERVICE",
    "category": "SOFTWARE",
    "image_url": "https://example.com/image.jpg",
    "home_url": "https://example.com/product",
    "create_time": "2024-01-01T00:00:00Z",
    "update_time": "2024-01-01T00:00:00Z",
}

SAMPLE_PRODUCTS_RESPONSE = {
    "products": [
        {"id": "PROD-123456789", "name": "Test Product"},
        {"id": "PROD-987654321", "name": "Another Product"},
    ],
    "links": [],
}

SAMPLE_TRANSACTION = {
    "transaction_info": {
        "transaction_id": "TXN-123456789",
        "transaction_event_code": "T0006",
        "transaction_initiation_date": "2024-01-15T10:30:00Z",
        "transaction_status": "S",
        "transaction_amount": {"value": "100.00", "currency_code": "USD"},
        "fee_amount": {"value": "3.50", "currency_code": "USD"},
    },
    "payer_info": {
        "email_address": "buyer@example.com",
        "payer_name": {"given_name": "John", "surname": "Doe"},
    },
}

SAMPLE_TRANSACTIONS_RESPONSE = {
    "transaction_details": [SAMPLE_TRANSACTION],
    "total_pages": 1,
    "total_items": 1,
}

SAMPLE_BALANCE = {
    "currency": "USD",
    "available_balance": {"value": "1000.00", "currency_code": "USD"},
    "withheld_balance": {"value": "50.00", "currency_code": "USD"},
    "total_balance": {"value": "1050.00", "currency_code": "USD"},
}

SAMPLE_BALANCES_RESPONSE = {
    "balances": [SAMPLE_BALANCE],
}

SAMPLE_DISPUTE = {
    "dispute_id": "PP-D-123456",
    "status": "OPEN",
    "reason": "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
    "dispute_amount": {"value": "50.00", "currency_code": "USD"},
    "create_time": "2024-01-10T00:00:00Z",
    "update_time": "2024-01-12T00:00:00Z",
}

SAMPLE_DISPUTES_RESPONSE = {
    "items": [SAMPLE_DISPUTE],
    "links": [],
}

SAMPLE_DISPUTE_DETAILS = {
    **SAMPLE_DISPUTE,
    "dispute_outcome": {
        "outcome_code": "RESOLVED_BUYER_FAVOUR",
        "amount_refunded": {"value": "50.00", "currency_code": "USD"},
    },
    "disputed_transactions": [
        {
            "seller_transaction_id": "TXN-987654321",
            "buyer": {"name": "Jane Buyer"},
        }
    ],
    "seller_response_due_date": "2024-01-20T00:00:00Z",
}
