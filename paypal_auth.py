"""
PayPal Authentication Module

Shared OAuth authentication for PayPal API utilities.
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from threading import Lock

import requests

CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
ENV = os.getenv("ENVIRONMENT", "dev")
TIMEOUT = int(os.getenv("PAYPAL_TIMEOUT", "30"))

if ENV == "prod":
    PAYPAL_API_BASE = "https://api.paypal.com"
else:
    PAYPAL_API_BASE = "https://api.sandbox.paypal.com"

_token_cache: dict = {"token": None, "expires_at": None, "lock": Lock()}

_EXPIRY_BUFFER_SECONDS = 300  # 5-minute buffer before token expiry


def clear_token_cache() -> None:
    """Reset the token cache. Used in tests to ensure clean state between runs."""
    _token_cache["token"] = None
    _token_cache["expires_at"] = None


def _is_cached_token_valid() -> bool:
    """Return True if the cached token exists and has not passed its expiry buffer."""
    token = _token_cache["token"]
    expires_at = _token_cache["expires_at"]
    if token is None or expires_at is None:
        return False
    return datetime.utcnow() < expires_at - timedelta(seconds=_EXPIRY_BUFFER_SECONDS)


def validate_credentials():
    """Validate that required credentials are set."""
    if CLIENT_ID is None:
        logging.error("PAYPAL_CLIENT_ID is not set")
        sys.exit(1)

    if PAYPAL_SECRET is None:
        logging.error("PAYPAL_SECRET is not set")
        sys.exit(1)


def get_paypal_token() -> str:
    """Obtain a PayPal API OAuth token, using the in-process cache when valid.

    The cache is checked under a lock to prevent redundant network calls in
    multi-threaded contexts. A 5-minute buffer is applied before the reported
    expiry so tokens are never used right up to their deadline.
    """
    with _token_cache["lock"]:
        if _is_cached_token_valid():
            return _token_cache["token"]

        validate_credentials()
        url = f"{PAYPAL_API_BASE}/v1/oauth2/token"
        headers = {"Accept": "application/json", "Accept-Language": "en_US"}
        response = requests.post(
            url,
            headers=headers,
            auth=(CLIENT_ID, PAYPAL_SECRET),
            data={"grant_type": "client_credentials"},
            timeout=TIMEOUT,
            verify=True,
        )
        response.raise_for_status()
        payload = response.json()
        access_token = payload["access_token"]
        expires_in = payload.get("expires_in", 32400)

        _token_cache["token"] = access_token
        _token_cache["expires_at"] = datetime.utcnow() + timedelta(seconds=expires_in)

        return access_token


def get_auth_headers() -> dict:
    """Get authorization headers for PayPal API requests."""
    access_token = get_paypal_token()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
