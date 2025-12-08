"""
PayPal Account Balance

CLI utility for viewing PayPal account balances.
"""

from datetime import datetime

import click
import requests

from paypal_auth import PAYPAL_API_BASE, get_auth_headers


def get_balances(as_of_date=None):
    """
    Fetch account balances from PayPal.

    Args:
        as_of_date (str): Optional date in ISO format to get historical balance

    Returns:
        list: List of balance records by currency
    """
    url = f"{PAYPAL_API_BASE}/v1/reporting/balances"
    headers = get_auth_headers()

    params = {}
    if as_of_date:
        params["as_of_time"] = as_of_date

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json().get("balances", [])
    else:
        click.echo(f"Failed to fetch balances: {response.status_code} - {response.text}")
        return []


@click.group()
def cli():
    """PayPal Account Balance CLI"""
    pass


@cli.command("show")
@click.option("--currency", "-c", help="Show only specific currency (e.g., USD, EUR)")
@click.option("--date", "-d", help="Historical balance as of date (YYYY-MM-DD)")
def cmd_show(currency, date):
    """Show current account balances."""
    as_of_date = None
    if date:
        as_of_date = f"{date}T23:59:59Z"
        click.echo(f"Balance as of {date}:")
    else:
        click.echo(f"Current Balance ({datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC):")

    balances = get_balances(as_of_date)

    if not balances:
        click.echo("No balance information available.")
        return

    click.echo("=" * 50)

    for balance in balances:
        curr = balance.get("currency", "USD")

        if currency and curr.upper() != currency.upper():
            continue

        available = balance.get("available_balance", {})
        withheld = balance.get("withheld_balance", {})
        total = balance.get("total_balance", {})

        click.echo(f"\n{curr}:")
        click.echo(f"  Available:  {float(available.get('value', 0)):>12,.2f}")

        if withheld.get("value"):
            click.echo(f"  Withheld:   {float(withheld.get('value', 0)):>12,.2f}")

        if total.get("value"):
            click.echo(f"  Total:      {float(total.get('value', 0)):>12,.2f}")


@cli.command("summary")
def cmd_summary():
    """Show a quick balance summary."""
    balances = get_balances()

    if not balances:
        click.echo("No balance information available.")
        return

    click.echo("Account Balance Summary:")
    click.echo("-" * 35)

    for balance in balances:
        curr = balance.get("currency", "USD")
        available = balance.get("available_balance", {})
        value = float(available.get("value", 0))
        click.echo(f"  {curr}: {value:>15,.2f}")


if __name__ == "__main__":
    cli()
