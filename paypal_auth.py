"""
PayPal Authentication Module

Shared OAuth authentication for PayPal API utilities.
"""

import logging
import os
import sys

import requests

CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
ENV = os.getenv("ENVIRONMENT", "dev")
TIMEOUT = int(os.getenv("PAYPAL_TIMEOUT", "30"))

if ENV == "prod":
    PAYPAL_API_BASE = "https://api.paypal.com"
else:
    PAYPAL_API_BASE = "https://api.sandbox.paypal.com"


def validate_credentials():
    """Validate that required credentials are set."""
    if CLIENT_ID is None:
        logging.error("PAYPAL_CLIENT_ID is not set")
        sys.exit(1)

    if PAYPAL_SECRET is None:
        logging.error("PAYPAL_SECRET is not set")
        sys.exit(1)


def get_paypal_token():
    """Obtain a PayPal API OAuth token."""
    validate_credentials()
    url = f"{PAYPAL_API_BASE}/v1/oauth2/token"
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    response = requests.post(
        url,
        headers=headers,
        auth=(CLIENT_ID, PAYPAL_SECRET),
        data={"grant_type": "client_credentials"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_auth_headers():
    """Get authorization headers for PayPal API requests."""
    access_token = get_paypal_token()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
