"""
PayPal Webhook Management

CLI utility for managing PayPal webhooks.
"""

import click
import requests

from paypal_auth import PAYPAL_API_BASE, TIMEOUT, create_session, get_auth_headers

_session = create_session()


def list_webhooks():
    """List current PayPal webhooks."""
    url = f"{PAYPAL_API_BASE}/v1/notifications/webhooks"
    headers = get_auth_headers()
    response = _session.get(url, headers=headers, timeout=TIMEOUT, verify=True)
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
    response = _session.post(webhook_url, headers=headers, json=payload, timeout=TIMEOUT, verify=True)
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
    response = _session.delete(url, headers=headers, timeout=TIMEOUT, verify=True)
    response.raise_for_status()

    click.echo(f"Webhook {webhook_id} deleted successfully.")
    return True


def get_webhook_event_catalog():
    """Return PayPal's available webhook event names and descriptions."""
    url = f"{PAYPAL_API_BASE}/v1/notifications/webhooks-event-types"
    headers = get_auth_headers()
    response = _session.get(url, headers=headers, timeout=TIMEOUT, verify=True)
    response.raise_for_status()

    return response.json().get("event_types", [])


def get_webhook_event_types():
    """List all available PayPal webhook event type names."""
    return [event_type["name"] for event_type in get_webhook_event_catalog()]


def parse_event_selection(selection, event_types):
    """Resolve a numbered interactive selection into webhook event names.

    Selections may contain comma-separated numbers and inclusive ranges, such
    as ``1,3-5``. ``all`` and ``*`` select every available event.
    """
    selection = selection.strip().lower()
    if selection in {"all", "*"}:
        return list(event_types)
    if not selection:
        raise ValueError("enter at least one event number")

    selected_indexes = []
    for part in selection.split(","):
        part = part.strip()
        if not part:
            raise ValueError("separate event numbers with a single comma")

        if "-" in part:
            bounds = [value.strip() for value in part.split("-")]
            if len(bounds) != 2 or not all(value.isdigit() for value in bounds):
                raise ValueError(f"'{part}' is not a valid range")
            start, end = (int(value) for value in bounds)
            if start > end:
                raise ValueError(f"range '{part}' must start with the lower number")
            indexes = range(start, end + 1)
        elif part.isdigit():
            indexes = [int(part)]
        else:
            raise ValueError(f"'{part}' is not an event number")

        for index in indexes:
            if not 1 <= index <= len(event_types):
                raise ValueError(
                    f"event number {index} is outside 1-{len(event_types)}"
                )
            zero_based_index = index - 1
            if zero_based_index not in selected_indexes:
                selected_indexes.append(zero_based_index)

    return [event_types[index] for index in selected_indexes]


def select_webhook_event_types(event_catalog):
    """Prompt the user to choose from the available webhook event types."""
    click.echo("\nAvailable webhook event types:")
    for index, event_type in enumerate(event_catalog, start=1):
        click.echo(f"  {index:>3}. {event_type['name']}")
        description = event_type.get("description")
        if description:
            click.echo(f"       {description}")

    click.echo(
        "\nSelect events by number. Use commas and ranges (for example, "
        "1,3-5), or enter 'all'."
    )
    event_types = [event_type["name"] for event_type in event_catalog]
    while True:
        selection = click.prompt("Events")
        try:
            selected_events = parse_event_selection(selection, event_types)
        except ValueError as exc:
            click.echo(f"Invalid selection: {exc}.", err=True)
            continue

        click.echo("\nSelected webhook events:")
        for event_type in selected_events:
            click.echo(f"  - {event_type}")

        if click.confirm("Use these events?", default=True):
            return selected_events
        click.echo("Choose the events again.")


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
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Choose event types from an interactive numbered list",
)
def cmd_create(url, events, all_events, interactive):
    """Create a webhook, prompting for events when none are supplied."""
    selection_modes = sum((bool(events), all_events, interactive))
    if selection_modes > 1:
        raise click.UsageError(
            "Use only one of --events, --all-events, or --interactive."
        )

    try:
        if all_events:
            event_types = get_webhook_event_types()
            if not event_types:
                click.echo("Could not retrieve event types.")
                return
        elif events:
            event_types = list(events)
        else:
            event_catalog = get_webhook_event_catalog()
            if not event_catalog:
                click.echo("Could not retrieve event types.")
                return
            event_types = select_webhook_event_types(event_catalog)

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
