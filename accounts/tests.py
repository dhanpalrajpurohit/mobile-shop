import json
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from products.models import Order, OrderItem, Product, ProductBrand


class AccountRoleBoundaryTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="customer",
            password="client-password-123",
        )
        self.admin_user = User.objects.create_user(
            username="store-admin",
            password="admin-password-123",
            is_staff=True,
        )
        self.root_user = User.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="root-password-123",
        )

    def test_client_login_is_limited_to_customer_accounts(self):
        response = self.client.post(reverse("signin"), {
            "username": self.admin_user.username,
            "password": "admin-password-123",
        })

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_client_can_sign_in_to_storefront(self):
        response = self.client.post(reverse("signin"), {
            "username": self.client_user.username,
            "password": "client-password-123",
        })

        self.assertRedirects(response, reverse("index"))
        self.assertEqual(self.client.get(reverse("cart")).status_code, 200)

    def test_store_admin_can_sign_in_to_custom_panel(self):
        response = self.client.post(reverse("admin_panel_login"), {
            "username": self.admin_user.username,
            "password": "admin-password-123",
        })

        self.assertRedirects(response, reverse("admin_panel_dashboard"))
        self.assertEqual(
            self.client.get(reverse("admin_panel_dashboard")).status_code,
            200,
        )

    def test_customer_cannot_sign_in_to_admin_panel(self):
        response = self.client.post(reverse("admin_panel_login"), {
            "username": self.client_user.username,
            "password": "client-password-123",
        })

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_store_admin_is_redirected_from_django_admin(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin:index"))

        self.assertRedirects(response, reverse("admin_panel_dashboard"))

    def test_root_can_access_django_admin_but_not_store_panel(self):
        self.client.force_login(self.root_user)

        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)
        self.assertRedirects(
            self.client.get(reverse("admin_panel_dashboard")),
            reverse("admin:index"),
        )

    def test_root_can_authenticate_through_django_admin_login(self):
        response = self.client.post(reverse("admin:login"), {
            "username": self.root_user.username,
            "password": "root-password-123",
            "next": reverse("admin:index"),
        })

        self.assertRedirects(response, reverse("admin:index"))
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)

    def test_root_cannot_authenticate_through_store_admin_login(self):
        response = self.client.post(reverse("admin_panel_login"), {
            "username": self.root_user.username,
            "password": "root-password-123",
        })

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_customer_is_redirected_from_django_admin(self):
        self.client.force_login(self.client_user)

        self.assertRedirects(self.client.get(reverse("admin:index")), reverse("index"))

    def test_admin_sign_in_is_rejected_by_root_django_admin_login(self):
        response = self.client.post(reverse("admin:login"), {
            "username": self.admin_user.username,
            "password": "admin-password-123",
            "next": reverse("admin:index"),
        })

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_panel_routes_render_for_store_admin(self):
        self.client.force_login(self.admin_user)

        for route_name in (
            "admin_panel_dashboard",
            "admin_panel_products",
            "admin_panel_product_create",
            "admin_panel_brands",
            "admin_panel_brand_create",
            "admin_panel_orders",
            "admin_sales_report",
        ):
            with self.subTest(route=route_name):
                self.assertEqual(self.client.get(reverse(route_name)).status_code, 200)

    def test_admin_can_access_storefront_and_customer_pages(self):
        self.client.force_login(self.admin_user)

        for route_name in ("index", "cart", "my_orders", "profile"):
            with self.subTest(route=route_name):
                self.assertEqual(self.client.get(reverse(route_name)).status_code, 200)

    def test_admin_dashboard_contains_sales_and_revenue_charts(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin_panel_dashboard"))

        self.assertContains(response, 'id="managerRevenueChart"')
        self.assertContains(response, 'id="managerOrdersChart"')
        self.assertContains(response, 'id="managerStatusChart"')

    def test_admin_dashboard_charts_use_ordered_sales_totals(self):
        brand = ProductBrand.objects.create(ProductBrand="Test brand")
        product = Product.objects.create(
            productName="Test phone",
            productSpecf="Test specs",
            productDesc="Test product description",
            productPrice=1500,
            productBrand=brand,
            stock=5,
        )
        order = Order.objects.create(
            user=self.client_user,
            total_amount=Decimal("3000.00"),
            shipping_address="Test address",
            phone="1234567890",
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=2,
            price=Decimal("1500.00"),
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin_panel_dashboard"))

        self.assertEqual(response.context["total_revenue"], Decimal("3000.00"))
        self.assertEqual(json.loads(response.context["revenue_data"]), [3000.0])
        self.assertEqual(json.loads(response.context["order_data"]), [1])

    def test_admin_storefront_nav_keeps_cart_and_order_links(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("index"))

        self.assertContains(response, reverse("cart"))
        self.assertContains(response, reverse("my_orders"))
        self.assertContains(response, reverse("admin_panel_dashboard"))

    def test_client_cannot_open_store_admin_panel(self):
        self.client.force_login(self.client_user)

        self.assertEqual(
            self.client.get(reverse("admin_panel_dashboard")).status_code,
            403,
        )
