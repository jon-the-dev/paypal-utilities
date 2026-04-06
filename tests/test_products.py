"""
Tests for paypal_products module.
"""

import csv
import os
import tempfile

import pytest
import requests
import responses
from click.testing import CliRunner

from conftest import (
    SAMPLE_PRODUCT,
    SAMPLE_PRODUCTS_RESPONSE,
    SANDBOX_API_BASE,
    TEST_ACCESS_TOKEN,
)


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing Click commands."""
    return CliRunner()


@pytest.fixture
def mock_auth():
    """Mock OAuth token endpoint."""
    responses.add(
        responses.POST,
        f"{SANDBOX_API_BASE}/v1/oauth2/token",
        json={"access_token": TEST_ACCESS_TOKEN},
        status=200,
    )


@pytest.fixture
def sample_csv_file():
    """Create a sample CSV file for import testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "description", "type", "category", "image_url", "home_url"])
        writer.writeheader()
        writer.writerow({
            "name": "Test Product 1",
            "description": "First test product",
            "type": "SERVICE",
            "category": "SOFTWARE",
            "image_url": "https://example.com/img1.jpg",
            "home_url": "https://example.com/product1",
        })
        writer.writerow({
            "name": "Test Product 2",
            "description": "Second test product",
            "type": "DIGITAL",
            "category": "DIGITAL_GOODS",
            "image_url": "",
            "home_url": "",
        })
        filepath = f.name

    yield filepath

    # Cleanup
    if os.path.exists(filepath):
        os.unlink(filepath)


class TestCreateProduct:
    """Tests for create_product function."""

    @responses.activate
    def test_create_product_success(self, mock_env_vars, mock_auth):
        """Test successful product creation."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json=SAMPLE_PRODUCT,
            status=201,
        )

        from paypal_products import create_product

        result = create_product(
            name="Test Product",
            description="A test product",
            product_type="SERVICE",
            category="SOFTWARE",
        )

        assert result is not None
        assert result["id"] == "PROD-123456789"
        assert result["name"] == "Test Product"

    @responses.activate
    def test_create_product_minimal(self, mock_env_vars, mock_auth):
        """Test creating product with minimal fields."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json={"id": "PROD-MIN", "name": "Minimal", "type": "SERVICE"},
            status=201,
        )

        from paypal_products import create_product

        result = create_product(name="Minimal")
        assert result is not None
        assert result["id"] == "PROD-MIN"

    @responses.activate
    def test_create_product_failure(self, mock_env_vars, mock_auth):
        """Test that product creation failure raises HTTPError."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json={"error": "invalid_request"},
            status=400,
        )

        from paypal_products import create_product

        with pytest.raises(requests.exceptions.HTTPError):
            create_product(name="")


class TestListProducts:
    """Tests for list_products function."""

    @responses.activate
    def test_list_products_success(self, mock_env_vars, mock_auth):
        """Test successful product listing."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json=SAMPLE_PRODUCTS_RESPONSE,
            status=200,
        )

        from paypal_products import list_products

        products = list_products()
        assert len(products) == 2
        assert products[0]["id"] == "PROD-123456789"

    @responses.activate
    def test_list_products_empty(self, mock_env_vars, mock_auth):
        """Test listing when no products exist."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json={"products": [], "links": []},
            status=200,
        )

        from paypal_products import list_products

        products = list_products()
        assert products == []

    @responses.activate
    def test_list_products_pagination(self, mock_env_vars, mock_auth):
        """Test product listing with pagination."""
        # First page
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json={
                "products": [{"id": "PROD-1", "name": "Product 1"}],
                "links": [{"rel": "next", "href": f"{SANDBOX_API_BASE}/v1/catalogs/products?page=2"}],
            },
            status=200,
        )
        # Second page
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/catalogs/products?page=2",
            json={
                "products": [{"id": "PROD-2", "name": "Product 2"}],
                "links": [],
            },
            status=200,
        )

        from paypal_products import list_products

        products = list_products()
        assert len(products) == 2


class TestGetProduct:
    """Tests for get_product function."""

    @responses.activate
    def test_get_product_success(self, mock_env_vars, mock_auth):
        """Test successful product retrieval."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/catalogs/products/PROD-123456789",
            json=SAMPLE_PRODUCT,
            status=200,
        )

        from paypal_products import get_product

        product = get_product("PROD-123456789")
        assert product is not None
        assert product["name"] == "Test Product"

    @responses.activate
    def test_get_product_not_found(self, mock_env_vars, mock_auth):
        """Test that getting non-existent product raises HTTPError."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/catalogs/products/PROD-INVALID",
            json={"error": "not_found"},
            status=404,
        )

        from paypal_products import get_product

        with pytest.raises(requests.exceptions.HTTPError):
            get_product("PROD-INVALID")


class TestUpdateProduct:
    """Tests for update_product function."""

    @responses.activate
    def test_update_product_success(self, mock_env_vars, mock_auth):
        """Test successful product update."""
        responses.add(
            responses.PATCH,
            f"{SANDBOX_API_BASE}/v1/catalogs/products/PROD-123456789",
            status=204,
        )

        from paypal_products import update_product

        result = update_product(
            "PROD-123456789",
            [{"op": "replace", "path": "/description", "value": "Updated description"}],
        )
        assert result is True

    @responses.activate
    def test_update_product_failure(self, mock_env_vars, mock_auth):
        """Test that product update failure raises HTTPError."""
        responses.add(
            responses.PATCH,
            f"{SANDBOX_API_BASE}/v1/catalogs/products/PROD-INVALID",
            json={"error": "not_found"},
            status=404,
        )

        from paypal_products import update_product

        with pytest.raises(requests.exceptions.HTTPError):
            update_product("PROD-INVALID", [])


class TestCSVImport:
    """Tests for CSV import functionality."""

    @responses.activate
    def test_import_from_csv_success(self, mock_env_vars, mock_auth, sample_csv_file):
        """Test successful CSV import."""
        # Mock product creation for each row
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json={"id": "PROD-NEW-1", "name": "Test Product 1"},
            status=201,
        )
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json={"id": "PROD-NEW-2", "name": "Test Product 2"},
            status=201,
        )

        from paypal_products import import_from_csv

        created, updated, failed = import_from_csv(sample_csv_file)
        assert created == 2
        assert updated == 0
        assert failed == 0

    @responses.activate
    def test_import_with_update_flag(self, mock_env_vars, mock_auth, sample_csv_file):
        """Test CSV import with update flag for existing products."""
        # Mock list products (for finding existing)
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json={
                "products": [{"id": "PROD-EXISTING", "name": "Test Product 1"}],
                "links": [],
            },
            status=200,
        )
        # Mock update for existing product
        responses.add(
            responses.PATCH,
            f"{SANDBOX_API_BASE}/v1/catalogs/products/PROD-EXISTING",
            status=204,
        )
        # Mock create for new product
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json={"id": "PROD-NEW", "name": "Test Product 2"},
            status=201,
        )

        from paypal_products import import_from_csv

        created, updated, failed = import_from_csv(sample_csv_file, update_existing=True)
        assert created == 1
        assert updated == 1
        assert failed == 0


class TestCSVExport:
    """Tests for CSV export functionality."""

    @responses.activate
    def test_export_to_csv_success(self, mock_env_vars, mock_auth):
        """Test successful CSV export."""
        # Mock list products
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json=SAMPLE_PRODUCTS_RESPONSE,
            status=200,
        )
        # Mock get product details for each
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/catalogs/products/PROD-123456789",
            json=SAMPLE_PRODUCT,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/catalogs/products/PROD-987654321",
            json={**SAMPLE_PRODUCT, "id": "PROD-987654321", "name": "Another Product"},
            status=200,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = f.name

        try:
            from paypal_products import export_to_csv

            count = export_to_csv(output_path)
            assert count == 2

            # Verify CSV content
            with open(output_path, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 2
                assert rows[0]["name"] == "Test Product"
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


    @responses.activate
    def test_export_to_csv_empty(self, mock_env_vars, mock_auth):
        """Test export when no products exist."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json={"products": [], "links": []},
            status=200,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = f.name

        try:
            from paypal_products import export_to_csv

            count = export_to_csv(output_path)
            assert count == 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestProductsCLI:
    """Tests for products CLI commands."""

    @responses.activate
    def test_cli_list_command(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI list command."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json=SAMPLE_PRODUCTS_RESPONSE,
            status=200,
        )

        from paypal_products import cli

        result = cli_runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "PROD-123456789" in result.output

    @responses.activate
    def test_cli_create_command(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI create command."""
        responses.add(
            responses.POST,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json=SAMPLE_PRODUCT,
            status=201,
        )

        from paypal_products import cli

        result = cli_runner.invoke(cli, [
            "create",
            "--name", "New Product",
            "--description", "A new product",
            "--type", "SERVICE",
        ])
        assert result.exit_code == 0
        assert "created successfully" in result.output

    def test_cli_template_command(self, mock_env_vars, cli_runner):
        """Test CLI template command."""
        from paypal_products import cli

        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(cli, ["template", "--output", "test_template.csv"])
            assert result.exit_code == 0
            assert os.path.exists("test_template.csv")

            # Verify template content
            with open("test_template.csv", "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 3  # Three example rows

    def test_cli_categories_command(self, mock_env_vars, cli_runner):
        """Test CLI categories command."""
        from paypal_products import cli

        result = cli_runner.invoke(cli, ["categories"])
        assert result.exit_code == 0
        assert "SOFTWARE" in result.output
        assert "PHYSICAL_GOODS" in result.output

    @responses.activate
    def test_cli_list_error_shows_error_output(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI list command shows error output on API failure."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/catalogs/products",
            json={"error": "unauthorized"},
            status=401,
        )

        from paypal_products import cli

        result = cli_runner.invoke(cli, ["list"])
        assert "Error" in result.output

    @responses.activate
    def test_cli_show_error_shows_error_output(self, mock_env_vars, mock_auth, cli_runner):
        """Test CLI show command shows error output on API failure."""
        responses.add(
            responses.GET,
            f"{SANDBOX_API_BASE}/v1/catalogs/products/PROD-INVALID",
            json={"error": "not_found"},
            status=404,
        )

        from paypal_products import cli

        result = cli_runner.invoke(cli, ["show", "PROD-INVALID"])
        assert "Error" in result.output
