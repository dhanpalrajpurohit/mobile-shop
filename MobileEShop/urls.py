"""MobileEShop URL Configuration"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from accounts.forms import RootAuthenticationForm
import sys
sys.path.append("..")
from products import views as product_view
from accounts import views as account_view

urlpatterns = [
    path('admin/', admin.site.urls),
    # Products & Shop
    path('shop/', include('products.urls')),
    path('<str:productName>/', product_view.ProductDetailView, name='product-detail'),
    path('', product_view.index, name='index'),
    # Accounts
    path('accounts/', include('accounts.urls')),
]

admin.site.login_form = RootAuthenticationForm

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)