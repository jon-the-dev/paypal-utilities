"""
PayPal Transaction History

CLI utility for downloading and viewing PayPal transaction history.
"""

import csv
from datetime import datetime, timedelta

import click
import requests

from paypal_auth import PAYPAL_API_BASE, TIMEOUT, get_auth_headers


def get_transactions(start_date, end_date, transaction_status=None, page_size=100):
    """
    Fetch transactions from PayPal.

    Args:
        start_date (str): Start date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
        end_date (str): End date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
        transaction_status (str): Optional filter by status (S=Success, D=Denied, P=Pending, V=Reversed)
        page_size (int): Number of records per page (max 500)

    Returns:
        list: List of transaction records
    """
    url = f"{PAYPAL_API_BASE}/v1/reporting/transactions"
    headers = get_auth_headers()

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "page_size": min(page_size, 500),
        "page": 1,
        "fields": "all",
    }

    if transaction_status:
        params["transaction_status"] = transaction_status

    all_transactions = []
    total_pages = 1

    while params["page"] <= total_pages:
        response = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            transactions = data.get("transaction_details", [])
            all_transactions.extend(transactions)

            total_pages = data.get("total_pages", 1)
            params["page"] += 1
        else:
            click.echo(f"Failed to fetch transactions: {response.status_code} - {response.text}")
            break

    return all_transactions


def format_transaction(txn):
    """Format a transaction for display."""
    info = txn.get("transaction_info", {})
    payer = txn.get("payer_info", {})

    return {
        "id": info.get("transaction_id", "N/A"),
        "date": info.get("transaction_initiation_date", "N/A")[:10],
        "type": info.get("transaction_event_code", "N/A"),
        "status": info.get("transaction_status", "N/A"),
        "amount": f"{info.get('transaction_amount', {}).get('value', '0.00')} {info.get('transaction_amount', {}).get('currency_code', 'USD')}",
        "fee": f"{info.get('fee_amount', {}).get('value', '0.00')} {info.get('fee_amount', {}).get('currency_code', 'USD')}" if info.get('fee_amount') else "N/A",
        "payer_email": payer.get("email_address", "N/A"),
        "payer_name": f"{payer.get('payer_name', {}).get('given_name', '')} {payer.get('payer_name', {}).get('surname', '')}".strip() or "N/A",
    }


def export_to_csv(transactions, filename):
    """Export transactions to CSV file."""
    if not transactions:
        click.echo("No transactions to export.")
        return

    formatted = [format_transaction(t) for t in transactions]

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=formatted[0].keys())
        writer.writeheader()
        writer.writerows(formatted)

    click.echo(f"Exported {len(formatted)} transactions to {filename}")


@click.group()
def cli():
    """PayPal Transaction History CLI"""
    pass


@cli.command("list")
@click.option("--start", "-s", help="Start date (YYYY-MM-DD)", default=None)
@click.option("--end", "-e", help="End date (YYYY-MM-DD)", default=None)
@click.option("--days", "-d", type=int, default=30, help="Number of days to look back (default: 30)")
@click.option("--status", type=click.Choice(["S", "D", "P", "V"]), help="Filter by status: S=Success, D=Denied, P=Pending, V=Reversed")
@click.option("--limit", "-l", type=int, default=20, help="Max transactions to display (default: 20)")
def cmd_list(start, end, days, status, limit):
    """List recent transactions."""
    if end:
        end_date = datetime.strptime(end, "%Y-%m-%d")
    else:
        end_date = datetime.utcnow()

    if start:
        start_date = datetime.strptime(start, "%Y-%m-%d")
    else:
        start_date = end_date - timedelta(days=days)

    start_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
    end_str = end_date.strftime("%Y-%m-%dT23:59:59Z")

    click.echo(f"Fetching transactions from {start_str[:10]} to {end_str[:10]}...")

    transactions = get_transactions(start_str, end_str, status)

    if not transactions:
        click.echo("No transactions found.")
        return

    click.echo(f"\nFound {len(transactions)} transactions (showing up to {limit}):\n")

    for txn in transactions[:limit]:
        fmt = format_transaction(txn)
        click.echo(f"  {fmt['date']} | {fmt['id'][:20]} | {fmt['status']:8} | {fmt['amount']:>15} | {fmt['payer_email']}")

    if len(transactions) > limit:
        click.echo(f"\n  ... and {len(transactions) - limit} more. Use --limit to see more or export to CSV.")


@cli.command("export")
@click.option("--start", "-s", help="Start date (YYYY-MM-DD)", default=None)
@click.option("--end", "-e", help="End date (YYYY-MM-DD)", default=None)
@click.option("--days", "-d", type=int, default=30, help="Number of days to look back (default: 30)")
@click.option("--status", type=click.Choice(["S", "D", "P", "V"]), help="Filter by status")
@click.option("--output", "-o", default="transactions.csv", help="Output filename (default: transactions.csv)")
def cmd_export(start, end, days, status, output):
    """Export transactions to CSV."""
    if end:
        end_date = datetime.strptime(end, "%Y-%m-%d")
    else:
        end_date = datetime.utcnow()

    if start:
        start_date = datetime.strptime(start, "%Y-%m-%d")
    else:
        start_date = end_date - timedelta(days=days)

    start_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
    end_str = end_date.strftime("%Y-%m-%dT23:59:59Z")

    click.echo(f"Fetching transactions from {start_str[:10]} to {end_str[:10]}...")

    transactions = get_transactions(start_str, end_str, status)
    export_to_csv(transactions, output)


@cli.command("summary")
@click.option("--start", "-s", help="Start date (YYYY-MM-DD)", default=None)
@click.option("--end", "-e", help="End date (YYYY-MM-DD)", default=None)
@click.option("--days", "-d", type=int, default=30, help="Number of days to look back (default: 30)")
def cmd_summary(start, end, days):
    """Show transaction summary with totals."""
    if end:
        end_date = datetime.strptime(end, "%Y-%m-%d")
    else:
        end_date = datetime.utcnow()

    if start:
        start_date = datetime.strptime(start, "%Y-%m-%d")
    else:
        start_date = end_date - timedelta(days=days)

    start_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
    end_str = end_date.strftime("%Y-%m-%dT23:59:59Z")

    click.echo(f"Fetching transactions from {start_str[:10]} to {end_str[:10]}...")

    transactions = get_transactions(start_str, end_str)

    if not transactions:
        click.echo("No transactions found.")
        return

    # Calculate summary by currency
    totals = {}
    fees = {}
    counts = {"S": 0, "D": 0, "P": 0, "V": 0}

    for txn in transactions:
        info = txn.get("transaction_info", {})
        amount_info = info.get("transaction_amount", {})
        fee_info = info.get("fee_amount", {})
        status = info.get("transaction_status", "")

        currency = amount_info.get("currency_code", "USD")
        amount = float(amount_info.get("value", 0))

        if currency not in totals:
            totals[currency] = 0
            fees[currency] = 0

        totals[currency] += amount

        if fee_info:
            fees[currency] += float(fee_info.get("value", 0))

        if status in counts:
            counts[status] += 1

    click.echo(f"\nTransaction Summary ({start_str[:10]} to {end_str[:10]}):")
    click.echo("=" * 50)
    click.echo(f"Total Transactions: {len(transactions)}")
    click.echo(f"  Successful: {counts['S']}")
    click.echo(f"  Pending:    {counts['P']}")
    click.echo(f"  Denied:     {counts['D']}")
    click.echo(f"  Reversed:   {counts['V']}")

    click.echo("\nAmounts by Currency:")
    for currency in totals:
        click.echo(f"  {currency}: {totals[currency]:,.2f} (fees: {fees[currency]:,.2f})")


if __name__ == "__main__":
    cli()
