import csv
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.utils.html import format_html
from django.urls import path
from django.db.models import Sum, Count
from django.shortcuts import render
from django.utils import timezone
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from .models import Product, ProductBrand, Cart, Order, OrderItem, Review


# ─── IMPORT/EXPORT RESOURCES ────────────────────────────────────────────────

class ProductResource(resources.ModelResource):
    brand = fields.Field(attribute='productBrand__ProductBrand', column_name='Brand')

    class Meta:
        model = Product
        fields = ('id', 'productName', 'brand', 'productSpecf', 'productPrice', 'stock')
        export_order = fields


class OrderResource(resources.ModelResource):
    customer = fields.Field(attribute='user__username', column_name='Customer')
    email = fields.Field(attribute='user__email', column_name='Email')

    class Meta:
        model = Order
        fields = ('id', 'customer', 'email', 'order_date', 'status',
                  'total_amount', 'payment_method', 'payment_status', 'phone')
        export_order = fields


class ReviewResource(resources.ModelResource):
    customer = fields.Field(attribute='user__username', column_name='Customer')
    product_name = fields.Field(attribute='product__productName', column_name='Product')

    class Meta:
        model = Review
        fields = ('id', 'customer', 'product_name', 'rating', 'title', 'created_at')


# ─── INLINE ADMINS ──────────────────────────────────────────────────────────

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price', 'subtotal_display')
    fields = ('product', 'quantity', 'price', 'subtotal_display')

    def subtotal_display(self, obj):
        return format_html('<strong>₹{:,.0f}</strong>', float(obj.subtotal()))
    subtotal_display.short_description = 'Subtotal'


# ─── ORDER ADMIN ─────────────────────────────────────────────────────────────

@admin.register(Order)
class OrderAdmin(ImportExportModelAdmin):
    resource_class = OrderResource
    list_display = (
        'order_id_display', 'customer_display', 'order_date', 'items_count',
        'total_display', 'payment_badge', 'status_badge', 'invoice_link'
    )
    list_filter = ('status', 'payment_method', 'payment_status', 'order_date')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone')
    readonly_fields = ('order_date', 'user', 'total_amount', 'items_summary')
    inlines = [OrderItemInline]
    date_hierarchy = 'order_date'
    list_per_page = 25
    actions = ['export_csv', 'mark_confirmed', 'mark_shipped', 'mark_delivered', 'mark_paid']

    fieldsets = (
        ('Order Info', {
            'fields': ('user', 'order_date', 'status', 'total_amount', 'items_summary')
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_status')
        }),
        ('Delivery', {
            'fields': ('shipping_address', 'phone', 'notes')
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(self.dashboard_view), name='order-dashboard'),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        """Custom dashboard with revenue chart data."""
        from django.db.models.functions import TruncMonth
        import json

        # Monthly revenue for last 6 months
        monthly = (Order.objects
                   .filter(order_date__gte=timezone.now() - timezone.timedelta(days=180))
                   .annotate(month=TruncMonth('order_date'))
                   .values('month')
                   .annotate(revenue=Sum('total_amount'), orders=Count('id'))
                   .order_by('month'))

        labels = [m['month'].strftime('%b %Y') for m in monthly]
        revenue_data = [float(m['revenue'] or 0) for m in monthly]
        order_data = [m['orders'] for m in monthly]

        # Stats
        total_revenue = Order.objects.aggregate(t=Sum('total_amount'))['t'] or 0
        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(status='pending').count()
        delivered_orders = Order.objects.filter(status='delivered').count()
        total_users = User.objects.filter(is_staff=False).count()
        total_products = Product.objects.count()

        # Top products
        top_products = (OrderItem.objects
                        .values('product__productName', 'product__productBrand__ProductBrand')
                        .annotate(qty=Sum('quantity'), rev=Sum('price'))
                        .order_by('-qty')[:8])

        # Recent orders
        recent_orders = Order.objects.select_related('user').order_by('-order_date')[:10]

        # Status breakdown
        status_counts = {s: Order.objects.filter(status=s).count()
                         for s, _ in Order.STATUS_CHOICES}

        # Payment methods distribution
        payment_counts = {p: Order.objects.filter(payment_method=p).count()
                          for p, _ in Order.PAYMENT_CHOICES}

        top_products_names = [p['product__productName'] for p in top_products]
        top_products_revenue = [float(p['rev'] or 0) for p in top_products]

        context = dict(
            self.admin_site.each_context(request),
            title='Sales Dashboard',
            labels=json.dumps(labels),
            revenue_data=json.dumps(revenue_data),
            order_data=json.dumps(order_data),
            total_revenue=total_revenue,
            total_orders=total_orders,
            pending_orders=pending_orders,
            delivered_orders=delivered_orders,
            total_users=total_users,
            total_products=total_products,
            top_products=top_products,
            recent_orders=recent_orders,
            status_counts=json.dumps(status_counts),
            payment_counts=json.dumps(payment_counts),
            top_products_names=json.dumps(top_products_names),
            top_products_revenue=json.dumps(top_products_revenue),
        )
        return render(request, 'admin/dashboard.html', context)

    # ── Display helpers ───────────────────────────────────────────────────────

    def order_id_display(self, obj):
        return format_html('<strong>INV-{:05d}</strong>', obj.id)
    order_id_display.short_description = 'Invoice'
    order_id_display.admin_order_field = 'id'

    def customer_display(self, obj):
        full = obj.user.get_full_name() or obj.user.username
        return format_html(
            '<div><strong>{}</strong></div><small style="color:#6b7280">{}</small>',
            full, obj.user.email
        )
    customer_display.short_description = 'Customer'
    customer_display.admin_order_field = 'user__username'

    def items_count(self, obj):
        count = obj.items.count()
        return format_html('<span class="badge badge-info">{} item{}</span>',
                           count, 's' if count != 1 else '')
    items_count.short_description = 'Items'

    def total_display(self, obj):
        return format_html('<strong>₹{:,.0f}</strong>', float(obj.total_amount))
    total_display.short_description = 'Total'
    total_display.admin_order_field = 'total_amount'

    def payment_badge(self, obj):
        colors = {'paid': 'success', 'pending': 'warning', 'failed': 'danger'}
        color = colors.get(obj.payment_status, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color, obj.payment_status.upper()
        )
    payment_badge.short_description = 'Payment'

    def status_badge(self, obj):
        colors = {
            'pending': 'warning', 'confirmed': 'info',
            'shipped': 'primary', 'delivered': 'success', 'cancelled': 'danger'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def invoice_link(self, obj):
        return format_html(
            '<a href="/shop/orders/{}/invoice/" target="_blank" '
            'class="btn btn-sm btn-outline-primary">'
            '<i class="fas fa-file-pdf"></i> PDF</a>', obj.id
        )
    invoice_link.short_description = 'Invoice'

    def items_summary(self, obj):
        rows = ''.join(
            f'<tr><td>{item.product.productName}</td>'
            f'<td>×{item.quantity}</td>'
            f'<td>₹{float(item.price):,.0f}</td>'
            f'<td><strong>₹{float(item.subtotal()):,.0f}</strong></td></tr>'
            for item in obj.items.all()
        )
        return format_html(
            '<table style="width:100%;border-collapse:collapse">'
            '<thead><tr style="background:#f1f5f9">'
            '<th style="padding:6px;text-align:left">Product</th>'
            '<th>Qty</th><th>Price</th><th>Subtotal</th>'
            '</tr></thead><tbody>{}</tbody>'
            '<tfoot><tr><td colspan="3"><strong>Total</strong></td>'
            '<td><strong>₹{:,.0f}</strong></td></tr></tfoot>'
            '</table>',
            format_html('{}', format_html(rows)), float(obj.total_amount)
        )
    items_summary.short_description = 'Items Detail'

    # ── Bulk actions ──────────────────────────────────────────────────────────

    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Invoice', 'Customer', 'Email', 'Phone', 'Date', 'Items',
                         'Total (Rs.)', 'Payment Method', 'Payment Status', 'Order Status', 'Address'])
        for o in queryset.prefetch_related('items').select_related('user'):
            products = '; '.join(f'{i.product.productName} x{i.quantity}' for i in o.items.all())
            writer.writerow([
                f'INV-{o.id:05d}', o.user.get_full_name() or o.user.username,
                o.user.email, o.phone, o.order_date.strftime('%Y-%m-%d %H:%M'),
                products, float(o.total_amount), o.get_payment_method_display(),
                o.payment_status, o.get_status_display(), o.shipping_address
            ])
        return response
    export_csv.short_description = '📥 Export selected as CSV'

    def mark_confirmed(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} order(s) marked as Confirmed.')
    mark_confirmed.short_description = '✅ Mark as Confirmed'

    def mark_shipped(self, request, queryset):
        updated = queryset.update(status='shipped')
        self.message_user(request, f'{updated} order(s) marked as Shipped.')
    mark_shipped.short_description = '🚚 Mark as Shipped'

    def mark_delivered(self, request, queryset):
        updated = queryset.update(status='delivered', payment_status='paid')
        self.message_user(request, f'{updated} order(s) marked as Delivered & Paid.')
    mark_delivered.short_description = '📦 Mark as Delivered + Paid'

    def mark_paid(self, request, queryset):
        updated = queryset.update(payment_status='paid')
        self.message_user(request, f'{updated} order(s) marked as Paid.')
    mark_paid.short_description = '💳 Mark as Paid'


# ─── PRODUCT ADMIN ──────────────────────────────────────────────────────────

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = ('product_image_thumb', 'productName', 'brand_display',
                    'productSpecf', 'price_display', 'stock_display', 'rating_display')
    list_filter = ('productBrand',)
    search_fields = ('productName', 'productDesc', 'productSpecf')
    list_editable = ('productPrice', 'stock') if False else ()  # enable inline editing below
    list_per_page = 20

    def product_image_thumb(self, obj):
        if obj.productImage:
            return format_html(
                '<img src="{}" style="width:48px;height:48px;object-fit:contain;'
                'border-radius:6px;background:#f1f5f9;padding:2px">',
                obj.productImage.url
            )
        return '—'
    product_image_thumb.short_description = ''

    def brand_display(self, obj):
        return format_html('<span class="badge badge-primary">{}</span>', obj.productBrand)
    brand_display.short_description = 'Brand'
    brand_display.admin_order_field = 'productBrand__ProductBrand'

    def price_display(self, obj):
        return format_html('<strong>₹{:,}</strong>', obj.productPrice)
    price_display.short_description = 'Price'
    price_display.admin_order_field = 'productPrice'

    def stock_display(self, obj):
        if obj.stock == 0:
            color = 'danger'
            text = 'Out of Stock'
        elif obj.stock < 5:
            color = 'warning'
            text = f'Low ({obj.stock})'
        else:
            color = 'success'
            text = str(obj.stock)
        return format_html('<span class="badge badge-{}">{}</span>', color, text)
    stock_display.short_description = 'Stock'
    stock_display.admin_order_field = 'stock'

    def rating_display(self, obj):
        avg = obj.average_rating()
        if avg:
            stars = '★' * int(avg) + '☆' * (5 - int(avg))
            return format_html(
                '<span style="color:#f59e0b">{}</span> <small>{}</small>',
                stars, avg
            )
        return format_html('<small style="color:#9ca3af">{}</small>', 'No reviews')
    rating_display.short_description = 'Rating'


# ─── REVIEW ADMIN ───────────────────────────────────────────────────────────

@admin.register(Review)
class ReviewAdmin(ImportExportModelAdmin):
    resource_class = ReviewResource
    list_display = ('star_display', 'product', 'reviewer_display', 'title', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'product__productName', 'title', 'body')
    readonly_fields = ('user', 'product', 'created_at')
    date_hierarchy = 'created_at'

    def star_display(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        colors = {1: '#ef4444', 2: '#f97316', 3: '#eab308', 4: '#84cc16', 5: '#22c55e'}
        return format_html(
            '<span style="color:{};font-size:16px">{}</span>',
            colors.get(obj.rating, '#f59e0b'), stars
        )
    star_display.short_description = 'Rating'

    def reviewer_display(self, obj):
        return format_html(
            '<strong>{}</strong><br><small style="color:#6b7280">{}</small>',
            obj.user.username, obj.user.email
        )
    reviewer_display.short_description = 'Reviewer'


# ─── CUSTOM USER ADMIN (no password visible) ─────────────────────────────────

class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'full_name_display', 'is_staff',
                    'is_active', 'date_joined', 'order_count', 'total_spent')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    readonly_fields = ('date_joined', 'last_login', 'order_summary')
    date_hierarchy = 'date_joined'

    fieldsets = (
        ('Account', {'fields': ('username', 'email', 'is_active')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Activity', {'fields': ('date_joined', 'last_login', 'order_summary')}),
    )
    # Remove password field from add form display
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_staff'),
        }),
    )

    def full_name_display(self, obj):
        name = obj.get_full_name()
        return format_html('<strong>{}</strong>', name) if name else format_html(
            '<em style="color:#9ca3af">—</em>')
    full_name_display.short_description = 'Full Name'

    def order_count(self, obj):
        count = obj.orders.count()
        if count:
            return format_html('<span class="badge badge-info">{}</span>', count)
        return '—'
    order_count.short_description = 'Orders'

    def total_spent(self, obj):
        total = obj.orders.aggregate(t=Sum('total_amount'))['t'] or 0
        if total:
            return format_html('<strong>₹{:,.0f}</strong>', float(total))
        return '—'
    total_spent.short_description = 'Total Spent'

    def order_summary(self, obj):
        orders = obj.orders.order_by('-order_date')[:5]
        if not orders:
            return 'No orders yet.'
        rows = ''.join(
            f'<tr>'
            f'<td><a href="/admin/products/order/{o.id}/change/">INV-{o.id:05d}</a></td>'
            f'<td>{o.order_date.strftime("%d %b %Y")}</td>'
            f'<td>₹{float(o.total_amount):,.0f}</td>'
            f'<td>{o.get_status_display()}</td>'
            f'</tr>'
            for o in orders
        )
        return format_html(
            '<table style="width:100%;border-collapse:collapse">'
            '<thead><tr style="background:#f1f5f9">'
            '<th style="padding:6px;text-align:left">Invoice</th>'
            '<th>Date</th><th>Amount</th><th>Status</th>'
            '</tr></thead><tbody>{}</tbody></table>',
            format_html('{}', format_html(rows))
        )
    order_summary.short_description = 'Recent Orders'


# Re-register User with custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ─── REMAINING MODELS ────────────────────────────────────────────────────────

@admin.register(ProductBrand)
class ProductBrandAdmin(admin.ModelAdmin):
    list_display = ('ProductBrand', 'product_count')
    search_fields = ('ProductBrand',)

    def product_count(self, obj):
        count = obj.product_set.count()
        return format_html('<span class="badge badge-secondary">{} product{}</span>',
                           count, 's' if count != 1 else '')
    product_count.short_description = 'Products'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity', 'subtotal_display', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('user__username', 'product__productName')
    readonly_fields = ('added_at',)

    def subtotal_display(self, obj):
        return format_html('<strong>₹{:,}</strong>', obj.subtotal())
    subtotal_display.short_description = 'Subtotal'


# ─── ADMIN SITE CUSTOMIZATION ────────────────────────────────────────────────

admin.site.site_header = '📱 MobileShop Admin'
admin.site.site_title = 'MobileShop Admin'
admin.site.index_title = 'Dashboard'