"""
PayPal Dispute Management

CLI utility for viewing and tracking PayPal disputes and chargebacks.
"""

from datetime import datetime, timedelta

import click
import requests

from paypal_auth import PAYPAL_API_BASE, TIMEOUT, get_auth_headers


# Dispute status codes
DISPUTE_STATUSES = [
    "OPEN",
    "WAITING_FOR_BUYER_RESPONSE",
    "WAITING_FOR_SELLER_RESPONSE",
    "UNDER_REVIEW",
    "RESOLVED",
    "OTHER",
]


def get_disputes(start_date=None, dispute_state=None, page_size=20):
    """
    Fetch disputes from PayPal.

    Args:
        start_date (str): Start date in ISO format
        dispute_state (str): Filter by dispute state
        page_size (int): Number of records per page

    Returns:
        list: List of dispute records
    """
    url = f"{PAYPAL_API_BASE}/v1/customer/disputes"
    headers = get_auth_headers()

    params = {
        "page_size": min(page_size, 50),
    }

    if start_date:
        params["start_time"] = start_date

    if dispute_state:
        params["dispute_state"] = dispute_state

    all_disputes = []

    while url:
        response = requests.get(url, headers=headers, params=params, timeout=TIMEOUT, verify=True)
        response.raise_for_status()

        data = response.json()
        disputes = data.get("items", [])
        all_disputes.extend(disputes)

        # Check for next page
        links = data.get("links", [])
        next_link = next((l for l in links if l.get("rel") == "next"), None)
        url = next_link.get("href") if next_link else None
        params = {}  # Clear params for next page (URL includes them)

    return all_disputes


def get_dispute_details(dispute_id):
    """
    Get detailed information about a specific dispute.

    Args:
        dispute_id (str): The dispute ID

    Returns:
        dict: Dispute details
    """
    url = f"{PAYPAL_API_BASE}/v1/customer/disputes/{dispute_id}"
    headers = get_auth_headers()

    response = requests.get(url, headers=headers, timeout=TIMEOUT, verify=True)
    response.raise_for_status()
    return response.json()


def format_dispute(dispute):
    """Format a dispute for display."""
    amount = dispute.get("dispute_amount", {})
    return {
        "id": dispute.get("dispute_id", "N/A"),
        "status": dispute.get("status", "N/A"),
        "reason": dispute.get("reason", "N/A"),
        "amount": f"{amount.get('value', '0.00')} {amount.get('currency_code', 'USD')}",
        "created": dispute.get("create_time", "N/A")[:10],
        "updated": dispute.get("update_time", "N/A")[:10],
    }


@click.group()
def cli():
    """PayPal Dispute Management CLI"""
    pass


@cli.command("list")
@click.option("--status", "-s", type=click.Choice(DISPUTE_STATUSES), help="Filter by dispute status")
@click.option("--days", "-d", type=int, default=90, help="Number of days to look back (default: 90)")
@click.option("--limit", "-l", type=int, default=20, help="Max disputes to display (default: 20)")
def cmd_list(status, days, limit):
    """List disputes."""
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")

    click.echo(f"Fetching disputes from the last {days} days...")

    try:
        disputes = get_disputes(start_date, status)
    except requests.exceptions.RequestException as exc:
        click.echo(f"Error: {exc}", err=True)
        return

    if not disputes:
        click.echo("No disputes found.")
        return

    click.echo(f"\nFound {len(disputes)} disputes (showing up to {limit}):\n")

    # Group by status
    by_status = {}
    for d in disputes:
        s = d.get("status", "UNKNOWN")
        if s not in by_status:
            by_status[s] = []
        by_status[s].append(d)

    count = 0
    for stat in DISPUTE_STATUSES:
        if stat in by_status and count < limit:
            click.echo(f"\n{stat}:")
            for dispute in by_status[stat]:
                if count >= limit:
                    break
                fmt = format_dispute(dispute)
                click.echo(f"  {fmt['created']} | {fmt['id']} | {fmt['amount']:>12} | {fmt['reason']}")
                count += 1


@cli.command("show")
@click.argument("dispute_id")
def cmd_show(dispute_id):
    """Show details for a specific dispute."""
    try:
        dispute = get_dispute_details(dispute_id)
    except requests.exceptions.RequestException as exc:
        click.echo(f"Error: {exc}", err=True)
        return

    amount = dispute.get("dispute_amount", {})
    outcome = dispute.get("dispute_outcome", {})

    click.echo(f"\nDispute Details: {dispute_id}")
    click.echo("=" * 60)
    click.echo(f"Status:       {dispute.get('status', 'N/A')}")
    click.echo(f"Reason:       {dispute.get('reason', 'N/A')}")
    click.echo(f"Amount:       {amount.get('value', '0.00')} {amount.get('currency_code', 'USD')}")
    click.echo(f"Created:      {dispute.get('create_time', 'N/A')}")
    click.echo(f"Updated:      {dispute.get('update_time', 'N/A')}")

    if outcome:
        click.echo(f"\nOutcome:")
        click.echo(f"  Code:       {outcome.get('outcome_code', 'N/A')}")
        refund = outcome.get("amount_refunded", {})
        if refund:
            click.echo(f"  Refunded:   {refund.get('value', '0.00')} {refund.get('currency_code', 'USD')}")

    # Transaction info
    txn_info = dispute.get("disputed_transactions", [])
    if txn_info:
        click.echo(f"\nDisputed Transactions:")
        for txn in txn_info:
            click.echo(f"  Transaction ID: {txn.get('seller_transaction_id', 'N/A')}")
            click.echo(f"  Buyer:          {txn.get('buyer', {}).get('name', 'N/A')}")

    # Response deadline
    if dispute.get("seller_response_due_date"):
        click.echo(f"\nResponse Due: {dispute.get('seller_response_due_date')}")


@cli.command("summary")
@click.option("--days", "-d", type=int, default=90, help="Number of days to look back (default: 90)")
def cmd_summary(days):
    """Show dispute summary."""
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")

    try:
        disputes = get_disputes(start_date)
    except requests.exceptions.RequestException as exc:
        click.echo(f"Error: {exc}", err=True)
        return

    if not disputes:
        click.echo("No disputes found.")
        return

    # Calculate summary
    by_status = {}
    total_amount = {}

    for dispute in disputes:
        status = dispute.get("status", "UNKNOWN")
        amount = dispute.get("dispute_amount", {})
        currency = amount.get("currency_code", "USD")
        value = float(amount.get("value", 0))

        if status not in by_status:
            by_status[status] = 0
        by_status[status] += 1

        if currency not in total_amount:
            total_amount[currency] = 0
        total_amount[currency] += value

    click.echo(f"\nDispute Summary (Last {days} days)")
    click.echo("=" * 40)
    click.echo(f"Total Disputes: {len(disputes)}")

    click.echo("\nBy Status:")
    for status in DISPUTE_STATUSES:
        if status in by_status:
            click.echo(f"  {status}: {by_status[status]}")

    click.echo("\nTotal Disputed Amount:")
    for currency, value in total_amount.items():
        click.echo(f"  {currency}: {value:,.2f}")

    # Action required
    action_required = by_status.get("WAITING_FOR_SELLER_RESPONSE", 0)
    if action_required > 0:
        click.echo(f"\n⚠️  {action_required} dispute(s) require your response!")


if __name__ == "__main__":
    cli()
