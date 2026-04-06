"""
PayPal Product Catalog Management

CLI utility for managing PayPal product catalog with CSV import/export.
Useful for merchants who want to manage their storefront products.
"""

import csv
import json
from pathlib import Path

import click
import requests

from paypal_auth import PAYPAL_API_BASE, TIMEOUT, get_auth_headers


# Valid product types
PRODUCT_TYPES = ["PHYSICAL", "DIGITAL", "SERVICE"]

# Common product categories
PRODUCT_CATEGORIES = [
    "SOFTWARE",
    "PHYSICAL_GOODS",
    "DIGITAL_GOODS",
    "DIGITAL_MEDIA",
    "SERVICES",
    "CLOTHING",
    "ELECTRONICS",
    "FOOD",
    "ACADEMIC_SOFTWARE",
    "ANTIQUES",
    "ART",
    "BEAUTY",
    "BOOKS",
    "BUSINESS",
    "CAMERAS",
    "CELL_PHONES",
    "COMPUTERS",
    "CONSULTING",
    "CRAFTS",
    "EDUCATION",
    "ENTERTAINMENT",
    "FINANCIAL_SERVICES",
    "FOOD_AND_GROCERY",
    "GIFTS",
    "GOVERNMENT",
    "HEALTH",
    "HOME_AND_GARDEN",
    "INSURANCE",
    "JEWELRY",
    "LEGAL",
    "MANUFACTURING",
    "MARKETING",
    "MEDIA",
    "MEDICAL",
    "MUSIC",
    "NONPROFIT",
    "PETS",
    "REAL_ESTATE",
    "RELIGION",
    "RESTAURANTS",
    "RETAIL",
    "SPORTS",
    "TELECOMMUNICATIONS",
    "TOYS",
    "TRANSPORTATION",
    "TRAVEL",
    "UTILITIES",
    "VIDEO",
    "OTHER",
]


def create_product(name, description=None, product_type="SERVICE", category=None, image_url=None, home_url=None):
    """
    Create a new product in PayPal catalog.

    Args:
        name (str): Product name (required)
        description (str): Product description
        product_type (str): PHYSICAL, DIGITAL, or SERVICE
        category (str): Product category
        image_url (str): URL to product image
        home_url (str): URL to product page

    Returns:
        dict: Created product or None on failure
    """
    url = f"{PAYPAL_API_BASE}/v1/catalogs/products"
    headers = get_auth_headers()

    payload = {
        "name": name,
        "type": product_type,
    }

    if description:
        payload["description"] = description
    if category:
        payload["category"] = category
    if image_url:
        payload["image_url"] = image_url
    if home_url:
        payload["home_url"] = home_url

    response = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT, verify=True)

    if response.status_code in [200, 201]:
        return response.json()
    else:
        click.echo(f"Failed to create product '{name}': {response.status_code} - {response.text}")
        return None


def list_products(page_size=20):
    """
    List all products in the catalog.

    Args:
        page_size (int): Number of products per page

    Returns:
        list: List of products
    """
    url = f"{PAYPAL_API_BASE}/v1/catalogs/products"
    headers = get_auth_headers()
    params = {"page_size": min(page_size, 20)}

    all_products = []

    while url:
        response = requests.get(url, headers=headers, params=params, timeout=TIMEOUT, verify=True)

        if response.status_code == 200:
            data = response.json()
            products = data.get("products", [])
            all_products.extend(products)

            # Check for next page
            links = data.get("links", [])
            next_link = next((link for link in links if link.get("rel") == "next"), None)
            url = next_link.get("href") if next_link else None
            params = {}  # Clear params for subsequent requests
        else:
            click.echo(f"Failed to list products: {response.status_code} - {response.text}")
            break

    return all_products


def get_product(product_id):
    """
    Get product details by ID.

    Args:
        product_id (str): The product ID

    Returns:
        dict: Product details or None
    """
    url = f"{PAYPAL_API_BASE}/v1/catalogs/products/{product_id}"
    headers = get_auth_headers()

    response = requests.get(url, headers=headers, timeout=TIMEOUT, verify=True)

    if response.status_code == 200:
        return response.json()
    else:
        click.echo(f"Failed to get product: {response.status_code} - {response.text}")
        return None


def update_product(product_id, updates):
    """
    Update a product using PATCH operations.

    Args:
        product_id (str): The product ID
        updates (list): List of patch operations

    Returns:
        bool: Success status
    """
    url = f"{PAYPAL_API_BASE}/v1/catalogs/products/{product_id}"
    headers = get_auth_headers()

    response = requests.patch(url, headers=headers, json=updates, timeout=TIMEOUT, verify=True)

    if response.status_code in [200, 204]:
        return True
    else:
        click.echo(f"Failed to update product: {response.status_code} - {response.text}")
        return False


def import_from_csv(filepath, update_existing=False):
    """
    Import products from a CSV file.

    Expected CSV columns: name, description, type, category, image_url, home_url

    Args:
        filepath (str): Path to CSV file
        update_existing (bool): If True, update products that already exist

    Returns:
        tuple: (created_count, updated_count, failed_count)
    """
    created = 0
    updated = 0
    failed = 0

    # Get existing products for update matching
    existing_products = {}
    if update_existing:
        for product in list_products(page_size=20):
            existing_products[product.get("name", "").lower()] = product.get("id")

    with open(filepath, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            name = row.get("name", "").strip()
            if not name:
                click.echo("Skipping row with empty name")
                failed += 1
                continue

            description = row.get("description", "").strip() or None
            product_type = row.get("type", "SERVICE").strip().upper()
            category = row.get("category", "").strip().upper() or None
            image_url = row.get("image_url", "").strip() or None
            home_url = row.get("home_url", "").strip() or None

            # Validate type
            if product_type not in PRODUCT_TYPES:
                click.echo(f"Invalid type '{product_type}' for '{name}', using SERVICE")
                product_type = "SERVICE"

            # Check if product exists (by name match)
            existing_id = existing_products.get(name.lower())

            if existing_id and update_existing:
                # Build patch operations
                patches = []
                if description:
                    patches.append({"op": "replace", "path": "/description", "value": description})
                if category:
                    patches.append({"op": "replace", "path": "/category", "value": category})
                if image_url:
                    patches.append({"op": "replace", "path": "/image_url", "value": image_url})
                if home_url:
                    patches.append({"op": "replace", "path": "/home_url", "value": home_url})

                if patches:
                    if update_product(existing_id, patches):
                        click.echo(f"Updated: {name}")
                        updated += 1
                    else:
                        failed += 1
                else:
                    click.echo(f"No updates for: {name}")
            else:
                # Create new product
                result = create_product(
                    name=name,
                    description=description,
                    product_type=product_type,
                    category=category,
                    image_url=image_url,
                    home_url=home_url,
                )
                if result:
                    click.echo(f"Created: {name} (ID: {result.get('id')})")
                    created += 1
                else:
                    failed += 1

    return created, updated, failed


def export_to_csv(filepath):
    """
    Export all products to a CSV file.

    Args:
        filepath (str): Output CSV path

    Returns:
        int: Number of products exported
    """
    products = list_products(page_size=20)

    if not products:
        click.echo("No products to export.")
        return 0

    # Fetch full details for each product
    detailed_products = []
    for product in products:
        details = get_product(product.get("id"))
        if details:
            detailed_products.append(details)

    fieldnames = ["id", "name", "description", "type", "category", "image_url", "home_url", "create_time", "update_time"]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for product in detailed_products:
            writer.writerow({
                "id": product.get("id", ""),
                "name": product.get("name", ""),
                "description": product.get("description", ""),
                "type": product.get("type", ""),
                "category": product.get("category", ""),
                "image_url": product.get("image_url", ""),
                "home_url": product.get("home_url", ""),
                "create_time": product.get("create_time", ""),
                "update_time": product.get("update_time", ""),
            })

    return len(detailed_products)


@click.group()
def cli():
    """PayPal Product Catalog Management CLI"""
    pass


@cli.command("list")
@click.option("--limit", "-l", type=int, default=20, help="Max products to display")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def cmd_list(limit, as_json):
    """List all products in the catalog."""
    products = list_products()

    if not products:
        click.echo("No products found.")
        return

    if as_json:
        click.echo(json.dumps(products[:limit], indent=2))
        return

    click.echo(f"Found {len(products)} products (showing up to {limit}):\n")

    for product in products[:limit]:
        click.echo(f"  {product.get('id', 'N/A')[:20]} | {product.get('name', 'N/A')[:40]}")


@cli.command("show")
@click.argument("product_id")
def cmd_show(product_id):
    """Show details for a specific product."""
    product = get_product(product_id)

    if not product:
        return

    click.echo(f"\nProduct: {product.get('name')}")
    click.echo("=" * 50)
    click.echo(f"ID:          {product.get('id')}")
    click.echo(f"Type:        {product.get('type')}")
    click.echo(f"Category:    {product.get('category', 'N/A')}")
    click.echo(f"Description: {product.get('description', 'N/A')}")
    click.echo(f"Image URL:   {product.get('image_url', 'N/A')}")
    click.echo(f"Home URL:    {product.get('home_url', 'N/A')}")
    click.echo(f"Created:     {product.get('create_time', 'N/A')}")
    click.echo(f"Updated:     {product.get('update_time', 'N/A')}")


@cli.command("create")
@click.option("--name", "-n", required=True, help="Product name")
@click.option("--description", "-d", help="Product description")
@click.option("--type", "product_type", type=click.Choice(PRODUCT_TYPES), default="SERVICE", help="Product type")
@click.option("--category", "-c", help="Product category (e.g., SOFTWARE, PHYSICAL_GOODS)")
@click.option("--image-url", help="URL to product image")
@click.option("--home-url", help="URL to product page")
def cmd_create(name, description, product_type, category, image_url, home_url):
    """Create a new product."""
    result = create_product(
        name=name,
        description=description,
        product_type=product_type,
        category=category.upper() if category else None,
        image_url=image_url,
        home_url=home_url,
    )

    if result:
        click.echo(f"Product created successfully!")
        click.echo(f"  ID: {result.get('id')}")
        click.echo(f"  Name: {result.get('name')}")


@cli.command("update")
@click.argument("product_id")
@click.option("--description", "-d", help="New description")
@click.option("--category", "-c", help="New category")
@click.option("--image-url", help="New image URL")
@click.option("--home-url", help="New home URL")
def cmd_update(product_id, description, category, image_url, home_url):
    """Update a product."""
    patches = []

    if description:
        patches.append({"op": "replace", "path": "/description", "value": description})
    if category:
        patches.append({"op": "replace", "path": "/category", "value": category.upper()})
    if image_url:
        patches.append({"op": "replace", "path": "/image_url", "value": image_url})
    if home_url:
        patches.append({"op": "replace", "path": "/home_url", "value": home_url})

    if not patches:
        click.echo("No updates specified. Use --description, --category, --image-url, or --home-url")
        return

    if update_product(product_id, patches):
        click.echo(f"Product {product_id} updated successfully!")


@cli.command("import")
@click.argument("csv_file", type=click.Path(exists=True))
@click.option("--update", "update_existing", is_flag=True, help="Update existing products by name match")
def cmd_import(csv_file, update_existing):
    """
    Import products from a CSV file.

    CSV columns: name, description, type, category, image_url, home_url
    """
    click.echo(f"Importing products from {csv_file}...")

    created, updated, failed = import_from_csv(csv_file, update_existing)

    click.echo(f"\nImport complete:")
    click.echo(f"  Created: {created}")
    click.echo(f"  Updated: {updated}")
    click.echo(f"  Failed:  {failed}")


@cli.command("export")
@click.option("--output", "-o", default="products.csv", help="Output CSV file (default: products.csv)")
def cmd_export(output):
    """Export all products to a CSV file."""
    click.echo(f"Exporting products to {output}...")

    count = export_to_csv(output)
    click.echo(f"Exported {count} products.")


@cli.command("template")
@click.option("--output", "-o", default="products_template.csv", help="Output template file")
def cmd_template(output):
    """Generate a CSV template for product import."""
    fieldnames = ["name", "description", "type", "category", "image_url", "home_url"]

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        # Write example rows
        writer.writerow({
            "name": "Example Physical Product",
            "description": "A sample physical product",
            "type": "PHYSICAL",
            "category": "PHYSICAL_GOODS",
            "image_url": "https://example.com/image.jpg",
            "home_url": "https://example.com/product",
        })
        writer.writerow({
            "name": "Example Digital Product",
            "description": "A sample digital download",
            "type": "DIGITAL",
            "category": "DIGITAL_GOODS",
            "image_url": "",
            "home_url": "https://example.com/download",
        })
        writer.writerow({
            "name": "Example Service",
            "description": "A sample service offering",
            "type": "SERVICE",
            "category": "SERVICES",
            "image_url": "",
            "home_url": "",
        })

    click.echo(f"Template created: {output}")
    click.echo("\nValid product types: PHYSICAL, DIGITAL, SERVICE")
    click.echo(f"Common categories: {', '.join(PRODUCT_CATEGORIES[:10])}...")


@cli.command("categories")
def cmd_categories():
    """List all valid product categories."""
    click.echo("Valid product categories:\n")
    for category in PRODUCT_CATEGORIES:
        click.echo(f"  - {category}")


if __name__ == "__main__":
    cli()
