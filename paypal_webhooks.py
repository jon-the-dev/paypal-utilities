"""
PayPal Webhook Management

CLI utility for managing PayPal webhooks.
"""

import click
import requests

from paypal_auth import PAYPAL_API_BASE, TIMEOUT, get_auth_headers


def list_webhooks():
    """List current PayPal webhooks."""
    url = f"{PAYPAL_API_BASE}/v1/notifications/webhooks"
    headers = get_auth_headers()
    response = requests.get(url, headers=headers, timeout=TIMEOUT, verify=True)
    response.raise_for_status()

    webhooks = response.json().get("webhooks", [])
    if not webhooks:
        click.echo("No webhooks configured.")
        return []

    click.echo("Current webhooks:")
    for webhook in webhooks:
        click.echo(f"\n  ID: {webhook['id']}")
        click.echo(f"  URL: {webhook['url']}")
        click.echo("  Event Types:")
        for eventtype in webhook.get("event_types", []):
            click.echo(f"    - {eventtype['name']}")
    return webhooks


def create_webhook(url, event_types):
    """
    Create a new PayPal webhook.

    Args:
        url (str): The URL for the webhook.
        event_types (list): List of event types to subscribe to.
    """
    headers = get_auth_headers()
    webhook_url = f"{PAYPAL_API_BASE}/v1/notifications/webhooks"
    payload = {
        "url": url,
        "event_types": [{"name": event_name} for event_name in event_types],
    }
    response = requests.post(webhook_url, headers=headers, json=payload, timeout=TIMEOUT, verify=True)
    response.raise_for_status()

    click.echo("Webhook created successfully.")
    webhook = response.json()
    click.echo(f"  ID: {webhook['id']}")
    click.echo(f"  URL: {webhook['url']}")
    return webhook


def delete_webhook(webhook_id):
    """
    Delete a PayPal webhook by its ID.

    Args:
        webhook_id (str): The ID of the webhook to be deleted.
    """
    url = f"{PAYPAL_API_BASE}/v1/notifications/webhooks/{webhook_id}"
    headers = get_auth_headers()
    response = requests.delete(url, headers=headers, timeout=TIMEOUT, verify=True)
    response.raise_for_status()

    click.echo(f"Webhook {webhook_id} deleted successfully.")
    return True


def get_webhook_event_types():
    """List all available PayPal webhook event types."""
    url = f"{PAYPAL_API_BASE}/v1/notifications/webhooks-event-types"
    headers = get_auth_headers()
    response = requests.get(url, headers=headers, timeout=TIMEOUT, verify=True)
    response.raise_for_status()

    event_types = response.json().get("event_types", [])
    return [et["name"] for et in event_types]


@click.group()
def cli():
    """PayPal Webhook Management CLI"""
    pass


@cli.command("list")
def cmd_list():
    """List all configured webhooks."""
    try:
        list_webhooks()
    except requests.exceptions.RequestException as exc:
        click.echo(f"Error: {exc}", err=True)


@cli.command("create")
@click.option("--url", "-u", required=True, help="Webhook endpoint URL")
@click.option("--events", "-e", multiple=True, help="Event types to subscribe to (can specify multiple)")
@click.option("--all-events", is_flag=True, help="Subscribe to all available event types")
def cmd_create(url, events, all_events):
    """Create a new webhook."""
    try:
        if all_events:
            event_types = get_webhook_event_types()
            if not event_types:
                click.echo("Could not retrieve event types.")
                return
        elif events:
            event_types = list(events)
        else:
            click.echo("Error: Specify --events or --all-events")
            return

        create_webhook(url, event_types)
    except requests.exceptions.RequestException as exc:
        click.echo(f"Error: {exc}", err=True)


@cli.command("delete")
@click.argument("webhook_id")
def cmd_delete(webhook_id):
    """Delete a webhook by ID."""
    try:
        delete_webhook(webhook_id)
    except requests.exceptions.RequestException as exc:
        click.echo(f"Error: {exc}", err=True)


@cli.command("events")
def cmd_events():
    """List all available webhook event types."""
    try:
        event_types = get_webhook_event_types()
        if event_types:
            click.echo("Available webhook event types:")
            for et in event_types:
                click.echo(f"  - {et}")
    except requests.exceptions.RequestException as exc:
        click.echo(f"Error: {exc}", err=True)


if __name__ == "__main__":
    cli()
