# paypal-utilities

A collection of CLI tools for PayPal merchants to manage products, webhooks, transactions, balances, and disputes.

## Installation

```bash
pip install -r requirements.txt
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PAYPAL_CLIENT_ID` | Yes | Your PayPal application client ID |
| `PAYPAL_SECRET` | Yes | Your PayPal application secret |
| `ENVIRONMENT` | No | Set to `prod` for production API (defaults to `dev`/sandbox) |

```bash
export PAYPAL_CLIENT_ID="your_client_id"
export PAYPAL_SECRET="your_secret"
export ENVIRONMENT="prod"  # Optional: use production API
```

## Scripts

### paypal_auth.py

Shared authentication module used by all other scripts. Handles OAuth token generation and provides common utilities.

---

### paypal_webhooks.py

Manage PayPal webhook subscriptions.

```bash
# List all configured webhooks
python paypal_webhooks.py list

# Create a webhook with specific events
python paypal_webhooks.py create --url https://example.com/webhook \
  -e PAYMENT.SALE.COMPLETED \
  -e PAYMENT.SALE.REFUNDED

# Create a webhook subscribed to all events
python paypal_webhooks.py create --url https://example.com/webhook --all-events

# Delete a webhook
python paypal_webhooks.py delete WEBHOOK_ID

# List available event types
python paypal_webhooks.py events
```

---

### paypal_transactions.py

Download and view transaction history with filtering and CSV export.

```bash
# List recent transactions (last 30 days)
python paypal_transactions.py list

# List transactions with date range
python paypal_transactions.py list --start 2024-01-01 --end 2024-01-31

# Filter by status (S=Success, D=Denied, P=Pending, V=Reversed)
python paypal_transactions.py list --status S

# Export to CSV
python paypal_transactions.py export --days 90 --output sales.csv

# Show summary with totals
python paypal_transactions.py summary --days 30
```

**Options:**

| Option | Description |
|--------|-------------|
| `--start`, `-s` | Start date (YYYY-MM-DD) |
| `--end`, `-e` | End date (YYYY-MM-DD) |
| `--days`, `-d` | Days to look back (default: 30) |
| `--status` | Filter: S=Success, D=Denied, P=Pending, V=Reversed |
| `--limit`, `-l` | Max records to display (default: 20) |
| `--output`, `-o` | CSV output filename |

---

### paypal_balance.py

View account balances by currency.

```bash
# Show current balances
python paypal_balance.py show

# Show balance for specific currency
python paypal_balance.py show --currency USD

# Show historical balance
python paypal_balance.py show --date 2024-01-15

# Quick summary
python paypal_balance.py summary
```

---

### paypal_disputes.py

Track and manage disputes and chargebacks.

```bash
# List disputes (last 90 days)
python paypal_disputes.py list

# Filter by status
python paypal_disputes.py list --status OPEN
python paypal_disputes.py list --status WAITING_FOR_SELLER_RESPONSE

# Show dispute details
python paypal_disputes.py show DISPUTE_ID

# Show dispute summary
python paypal_disputes.py summary --days 90
```

**Dispute Statuses:**

- `OPEN` - Dispute is open
- `WAITING_FOR_BUYER_RESPONSE` - Awaiting buyer input
- `WAITING_FOR_SELLER_RESPONSE` - Requires your response
- `UNDER_REVIEW` - PayPal is reviewing
- `RESOLVED` - Dispute closed
- `OTHER` - Other status

---

### paypal_products.py

Manage product catalog with CSV import/export for storefront management.

```bash
# Generate a CSV template
python paypal_products.py template --output my_products.csv

# Import products from CSV
python paypal_products.py import products.csv

# Import and update existing products (matched by name)
python paypal_products.py import products.csv --update

# Export current catalog to CSV
python paypal_products.py export --output catalog_backup.csv

# List all products
python paypal_products.py list

# Show product details
python paypal_products.py show PRODUCT_ID

# Create a single product
python paypal_products.py create --name "My Product" \
  --description "Product description" \
  --type SERVICE \
  --category SOFTWARE

# Update a product
python paypal_products.py update PRODUCT_ID \
  --description "New description" \
  --category DIGITAL_GOODS

# List valid categories
python paypal_products.py categories
```

**CSV Format:**

| Column | Required | Description |
|--------|----------|-------------|
| `name` | Yes | Product name |
| `description` | No | Product description |
| `type` | No | PHYSICAL, DIGITAL, or SERVICE (default: SERVICE) |
| `category` | No | Product category (e.g., SOFTWARE, PHYSICAL_GOODS) |
| `image_url` | No | URL to product image |
| `home_url` | No | URL to product page |

**Workflow for daily pricing/catalog updates:**

1. Export current catalog: `python paypal_products.py export -o catalog.csv`
2. Edit CSV in Excel/Google Sheets
3. Import changes: `python paypal_products.py import catalog.csv --update`

## Testing

The test suite uses pytest with mocked API responses (no PayPal credentials required).

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific test file
pytest tests/test_products.py

# Run specific test class
pytest tests/test_webhooks.py::TestCreateWebhook

# Run with verbose output
pytest -v
```

### Test Structure

Tests use the `responses` library to mock PayPal API calls, allowing validation of:

- API request/response handling
- Error handling and edge cases
- CSV import/export functionality
- CLI command behavior

## Project Structure

```text
paypal-utilities/
├── paypal_auth.py          # Shared OAuth authentication
├── paypal_products.py      # Product catalog management
├── paypal_webhooks.py      # Webhook management
├── paypal_transactions.py  # Transaction history & export
├── paypal_balance.py       # Account balance
├── paypal_disputes.py      # Dispute tracking
├── requirements.txt        # Dependencies
├── pytest.ini              # Test configuration
├── tests/
│   ├── conftest.py         # Shared fixtures & mock data
│   ├── test_auth.py
│   ├── test_balance.py
│   ├── test_disputes.py
│   ├── test_products.py
│   ├── test_transactions.py
│   └── test_webhooks.py
└── README.md
```

## License

AGPL-3.0
