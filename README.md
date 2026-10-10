# MobileShop

MobileShop is a Django storefront for browsing and purchasing mobile phones, with a separate store-management panel for staff. It has three account levels: **client**, **admin**, and **root**. Store admins use the storefront-styled management panel; root users retain the built-in Django administration site.

## Features

### Storefront and client accounts

- Browse the product catalogue and search by product name.
- Filter products by brand or price range.
- View product descriptions, specifications, stock, and customer reviews.
- Sign up and sign in as a client; manage account details and profile picture.
- Add products to a personal cart, adjust quantities, remove items, and review totals.
- Place an order with delivery information and a selected payment method.
- View personal order history and order details, and download a PDF invoice.
- Change a password and use the password-reset flow.

### Store admin panel

- Review store totals and recent activity on a dashboard.
- View revenue by month, monthly order volume, and order-status charts.
- Search products; add, edit, and delete products, including stock and product images.
- Add, edit, and delete brands. A brand with products cannot be deleted.
- Search and filter orders and update their fulfilment status.
- Review sales totals, orders, and best-selling products; export the sales report as CSV.
- Browse the public storefront and use client shopping flows while signed in, where applicable.

### Root administration

- Use Django's built-in admin to manage Django users and application records.
- Create and maintain store admin accounts.
- Access to `/admin/` is reserved for active root users (`is_staff=True` and `is_superuser=True`).

## Roles and sign-in

| Role | Account flags | Sign-in page | Main access |
| --- | --- | --- | --- |
| Client | `is_staff=False`, `is_superuser=False` | [`/accounts/login/`](http://localhost:8000/accounts/login/) | Storefront, personal profile, cart, checkout, reviews, and own orders |
| Admin | `is_staff=True`, `is_superuser=False` | [`/shop/admin/login/`](http://localhost:8000/shop/admin/login/) | Store-management panel and storefront |
| Root | `is_staff=True`, `is_superuser=True` | [`/admin/`](http://localhost:8000/admin/) | Django administration |

Public registration creates client accounts only. A root user provisions store admins through Django admin by enabling **Staff status** and leaving **Superuser status** disabled. The client login rejects staff accounts, the store-admin login rejects clients and root accounts, and the Django admin login is restricted to root accounts.

## User flows

### Client purchase

1. Open the storefront and search or filter the catalogue.
2. Open a product to review details and customer reviews.
3. Sign in or create a client account, then add products to the cart.
4. Update cart quantities or remove items, then continue to checkout.
5. Enter delivery information, choose a payment method, and place the order.
6. View the order from the account's order history and download its invoice.

### Store administration

1. Sign in at `/shop/admin/login/` with a store-admin account.
2. Use the dashboard charts and recent orders to review activity.
3. Maintain the catalogue and brands from the Products and Brands sections.
4. Search/filter orders and update order statuses.
5. Review sales and top-selling products, then export the report when needed.

### Root account provisioning

1. Sign in to Django admin at `/admin/` as a root user.
2. Create or select a user account.
3. Enable **Staff status** and ensure **Superuser status** remains disabled to grant store-admin access.

## Screenshots

These screenshots show the main storefront, account, shopping, and management screens. Customer-identifying text is obscured in captures; the profile photo has been replaced with a neutral placeholder. Catalogue and order figures are example local application data.

### Storefront and client

| Screen | Preview |
| --- | --- |
| Storefront catalogue, search, brand and price filters | ![Storefront catalogue](pictures/features/storefront.png) |
| Product details and reviews | ![Product details](pictures/features/product-detail.png) |
| Client sign-in | ![Client sign-in](pictures/features/client-sign-in.png) |
| Shopping cart and quantity controls | ![Shopping cart](pictures/features/shopping-cart.png) |
| Checkout and payment-method selection | ![Checkout](pictures/features/checkout.png) |
| Client profile and account editing (personal details redacted) | ![Client profile](pictures/features/profile.png) |

### Admin panel

| Screen | Preview |
| --- | --- |
| Store-admin sign-in | ![Store admin sign-in](pictures/features/admin-sign-in.png) |
| Dashboard and sales charts | ![Store admin dashboard](pictures/features/admin-dashboard.png) |
| Product catalogue management | ![Admin product list](pictures/features/admin-products.png) |
| Add/edit product form | ![Admin product form](pictures/features/admin-product-form.png) |
| Brand management | ![Admin brand list](pictures/features/admin-brands.png) |
| Add/edit brand form | ![Admin brand form](pictures/features/admin-brand-form.png) |
| Order search, filters, and status management | ![Admin orders](pictures/features/admin-orders.png) |
| Sales report and CSV export | ![Admin sales report](pictures/features/admin-sales-report.png) |

### Root administration

| Screen | Preview |
| --- | --- |
| Root sign-in to Django admin | ![Root sign-in](pictures/features/root-sign-in.png) |

## Routes at a glance

| Area | Routes |
| --- | --- |
| Storefront | `/`, `/<productName>/` |
| Client accounts | `/accounts/signup/`, `/accounts/login/`, `/accounts/profile/`, `/accounts/change_password/`, `/accounts/password_reset/` |
| Shopping | `/shop/cart/`, `/shop/checkout/`, `/shop/orders/`, `/shop/orders/<order_id>/`, `/shop/orders/<order_id>/invoice/` |
| Store admin | `/shop/admin/login/`, `/shop/admin/`, `/shop/admin/products/`, `/shop/admin/brands/`, `/shop/admin/orders/` |
| Sales reporting | `/shop/admin-report/`, `/shop/admin-report/export/` |
| Root administration | `/admin/` |

## Requirements

- Python 3.12.1 (the version pinned in `requirements.txt`)
- pip

The dependency manifest pins Django and the packages used by the project, including Pillow for image handling and ReportLab for PDF invoices. SQLite is configured as the default database.

## Run locally (Windows)

From the repository directory, create and activate a virtual environment, then install the pinned dependencies:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Apply database migrations and create the initial root account:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

Start the development server:

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. The built-in SQLite database is `db.sqlite3`. For local development, Django serves uploaded media while `DEBUG` is enabled. Configure `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, email, and a production database appropriately before deployment; the checked-in development settings are not production-ready.

## Payment note

Checkout offers Cash on Delivery, online payment, and card as order payment-method choices. The project does **not** integrate a payment gateway or capture real payments; selecting an online/card option should not be treated as proof that a transaction was processed.

## Tests

Run the Django test suite with:

```powershell
python manage.py test
```

## Project structure

- `accounts/` — account forms, role-aware authentication, profile model, and access controls.
- `products/` — catalogue, cart, orders, reviews, store-admin views, and sales reporting.
- `templates/` — storefront, account, and store-admin templates.
- `static/` — styles and other static assets.
- `pictures/features/` — screenshots used in this guide.

## Author

Dhanpal Singh Rajpurohit
