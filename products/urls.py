from django.urls import path
from accounts.views import AdminPanelLoginView
from . import views

urlpatterns = [
    path('admin/login/', AdminPanelLoginView.as_view(template_name='manager/login.html'), name='admin_panel_login'),
    path('admin/', views.admin_panel_dashboard, name='admin_panel_dashboard'),
    path('admin/products/', views.admin_panel_products, name='admin_panel_products'),
    path('admin/products/add/', views.admin_panel_product_create, name='admin_panel_product_create'),
    path('admin/products/<int:product_id>/edit/', views.admin_panel_product_update, name='admin_panel_product_update'),
    path('admin/products/<int:product_id>/delete/', views.admin_panel_product_delete, name='admin_panel_product_delete'),
    path('admin/brands/', views.admin_panel_brands, name='admin_panel_brands'),
    path('admin/brands/add/', views.admin_panel_brand_create, name='admin_panel_brand_create'),
    path('admin/brands/<int:brand_id>/edit/', views.admin_panel_brand_update, name='admin_panel_brand_update'),
    path('admin/brands/<int:brand_id>/delete/', views.admin_panel_brand_delete, name='admin_panel_brand_delete'),
    path('admin/orders/', views.admin_panel_orders, name='admin_panel_orders'),
    path('admin/orders/<int:order_id>/', views.admin_panel_order_update, name='admin_panel_order_update'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:cart_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:cart_id>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.my_orders, name='my_orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/invoice/', views.generate_invoice, name='generate_invoice'),
    path('review/add/<str:productName>/', views.add_review, name='add_review'),
    path('review/delete/<int:review_id>/', views.delete_review, name='delete_review'),
    path('admin-report/', views.admin_sales_report, name='admin_sales_report'),
    path('admin-report/export/', views.export_sales_csv, name='export_sales_csv'),
]
