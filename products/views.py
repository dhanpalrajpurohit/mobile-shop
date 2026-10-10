import csv
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.views.decorators.http import require_POST
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from accounts.decorators import admin_panel_required, client_required
from .forms import OrderStatusForm, ProductBrandForm, ProductForm
from .models import Product, ProductBrand, Cart, Order, OrderItem, Review


# ─── STOREFRONT ───────────────────────────────────────────────────────────────

def index(request):
    product = Product.objects.all()
    productBrand = ProductBrand.objects.all()
    brandID = request.GET.get('brandID')
    price = request.GET.get('price')
    search = request.POST.get('txt_searchbox') or request.GET.get('q')

    if brandID:
        product = Product.objects.filter(productBrand_id=brandID)
    elif price:
        product = Product.objects.filter(productPrice__lte=price)
    elif search:
        product = Product.objects.filter(productName__icontains=search)

    cart_count = 0
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).aggregate(
            total=Sum('quantity'))['total'] or 0

    data = {
        'products': product,
        'productBrands': productBrand,
        'cart_count': cart_count,
        'search_query': search or '',
        'selected_brand': brandID,
    }
    return render(request, 'index.html', data)


def ProductDetailView(request, productName):
    product = get_object_or_404(Product, productName=productName)
    productBrand = ProductBrand.objects.all()
    reviews = product.reviews.select_related('user').order_by('-created_at')
    user_review = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(product=product, user=request.user).first()

    cart_count = 0
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).aggregate(
            total=Sum('quantity'))['total'] or 0

    data = {
        'product': product,
        'products': [product],   # keep backward compat
        'productBrands': productBrand,
        'reviews': reviews,
        'user_review': user_review,
        'cart_count': cart_count,
    }
    return render(request, 'product_detail.html', data)


# ─── REVIEWS ──────────────────────────────────────────────────────────────────

@client_required
def add_review(request, productName):
    product = get_object_or_404(Product, productName=productName)
    if request.method == 'POST':
        rating = request.POST.get('rating')
        title = request.POST.get('title', '')
        body = request.POST.get('body', '')
        Review.objects.update_or_create(
            product=product, user=request.user,
            defaults={'rating': rating, 'title': title, 'body': body}
        )
        messages.success(request, 'Your review has been submitted!')
    return redirect('product-detail', productName=productName)


@client_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    productName = review.product.productName
    review.delete()
    messages.success(request, 'Review deleted.')
    return redirect('product-detail', productName=productName)


# ─── CART ─────────────────────────────────────────────────────────────────────

@client_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    total = sum(item.subtotal() for item in cart_items)
    cart_count = cart_items.aggregate(total=Sum('quantity'))['total'] or 0
    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total': total,
        'cart_count': cart_count,
    })


@client_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, f'"{product.productName}" added to cart!')
    next_url = request.META.get('HTTP_REFERER', '/')
    return redirect(next_url)


@client_required
def remove_from_cart(request, cart_id):
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
    cart_item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('cart')


@client_required
def update_cart(request, cart_id):
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
    qty = int(request.POST.get('quantity', 1))
    if qty > 0:
        cart_item.quantity = qty
        cart_item.save()
    else:
        cart_item.delete()
    return redirect('cart')


# ─── CHECKOUT & ORDERS ────────────────────────────────────────────────────────

@client_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty!')
        return redirect('cart')

    total = sum(item.subtotal() for item in cart_items)
    cart_count = cart_items.aggregate(total=Sum('quantity'))['total'] or 0

    if request.method == 'POST':
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()
        payment_method = request.POST.get('payment_method', 'cod')
        notes = request.POST.get('notes', '')

        if not address or not phone:
            messages.error(request, 'Address and phone are required.')
            return render(request, 'checkout.html', {
                'cart_items': cart_items, 'total': total, 'cart_count': cart_count
            })

        order = Order.objects.create(
            user=request.user,
            shipping_address=address,
            phone=phone,
            payment_method=payment_method,
            notes=notes,
            total_amount=total,
            status='confirmed',
            payment_status='paid' if payment_method != 'cod' else 'pending',
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.productPrice,
            )
        cart_items.delete()
        messages.success(request, f'Order #{order.id} placed successfully!')
        return redirect('order_detail', order_id=order.id)

    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'total': total,
        'cart_count': cart_count,
    })


@client_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product').order_by('-order_date')
    cart_count = Cart.objects.filter(user=request.user).aggregate(
        total=Sum('quantity'))['total'] or 0
    return render(request, 'my_orders.html', {'orders': orders, 'cart_count': cart_count})


@client_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    cart_count = Cart.objects.filter(user=request.user).aggregate(
        total=Sum('quantity'))['total'] or 0
    return render(request, 'order_detail.html', {'order': order, 'cart_count': cart_count})


@login_required
def generate_invoice(request, order_id):
    """Generate PDF invoice for a specific order."""
    if request.user.is_superuser:
        return redirect('admin:index')
    if request.user.is_staff:
        order = get_object_or_404(Order, id=order_id)
    else:
        order = get_object_or_404(Order, id=order_id, user=request.user)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30,
                            topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    # Header
    title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                 fontSize=24, textColor=colors.HexColor('#6366f1'),
                                 spaceAfter=4)
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'],
                               fontSize=10, textColor=colors.HexColor('#6b7280'))
    story.append(Paragraph('MobileShop', title_style))
    story.append(Paragraph('Your Premium Mobile Store', sub_style))
    story.append(Spacer(1, 20))

    # Invoice details
    invoice_data = [
        ['Invoice No:', f'INV-{order.id:05d}'],
        ['Order Date:', order.order_date.strftime('%d %b %Y, %I:%M %p')],
        ['Customer:', order.user.get_full_name() or order.user.username],
        ['Email:', order.user.email],
        ['Phone:', order.phone],
        ['Payment Method:', order.get_payment_method_display()],
        ['Payment Status:', order.payment_status.upper()],
        ['Order Status:', order.get_status_display()],
        ['Shipping Address:', order.shipping_address],
    ]
    inv_table = Table(invoice_data, colWidths=[2 * inch, 4 * inch])
    inv_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(inv_table)
    story.append(Spacer(1, 20))

    # Items table
    story.append(Paragraph('Order Items', styles['Heading2']))
    story.append(Spacer(1, 8))
    items_data = [['#', 'Product', 'Brand', 'Qty', 'Unit Price', 'Subtotal']]
    for i, item in enumerate(order.items.all(), 1):
        items_data.append([
            str(i),
            item.product.productName,
            str(item.product.productBrand),
            str(item.quantity),
            f'Rs. {item.price:,.0f}',
            f'Rs. {item.subtotal():,.0f}',
        ])
    items_data.append(['', '', '', '', 'TOTAL', f'Rs. {order.total_amount:,.0f}'])

    col_widths = [0.4 * inch, 2.2 * inch, 1.2 * inch, 0.5 * inch, 1 * inch, 1 * inch]
    items_table = Table(items_data, colWidths=col_widths)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.HexColor('#f9fafb'), colors.white]),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e7ff')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#4338ca')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 30))

    # Footer
    story.append(Paragraph('Thank you for shopping with MobileShop!', sub_style))
    story.append(Paragraph('For support: support@mobileshop.com | +91-9999999999', sub_style))

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice-INV{order.id:05d}.pdf"'
    return response


# ─── ADMIN REPORTS ────────────────────────────────────────────────────────────

@admin_panel_required
def admin_sales_report(request):
    orders = Order.objects.prefetch_related('items__product', 'user').order_by('-order_date')
    total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders = orders.count()
    delivered = orders.filter(status='delivered').count()
    pending = orders.filter(status='pending').count()

    # Top selling products
    top_products = (OrderItem.objects
                    .values('product__productName', 'product__productBrand__ProductBrand')
                    .annotate(total_qty=Sum('quantity'), total_revenue=Sum('price'))
                    .order_by('-total_qty')[:10])

    return render(request, 'admin_report.html', {
        'orders': orders,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'delivered': delivered,
        'pending': pending,
        'top_products': top_products,
    })


@admin_panel_required
def export_sales_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Customer', 'Email', 'Date', 'Products', 'Total (Rs.)',
                     'Payment Method', 'Payment Status', 'Order Status', 'Phone', 'Address'])
    orders = Order.objects.prefetch_related('items__product').select_related('user').order_by('-order_date')
    for order in orders:
        products_str = '; '.join(
            [f"{item.product.productName} x{item.quantity}" for item in order.items.all()]
        )
        writer.writerow([
            f'INV-{order.id:05d}',
            order.user.get_full_name() or order.user.username,
            order.user.email,
            order.order_date.strftime('%Y-%m-%d %H:%M'),
            products_str,
            float(order.total_amount),
            order.get_payment_method_display(),
            order.payment_status,
            order.get_status_display(),
            order.phone,
            order.shipping_address,
        ])
    return response


# ─── STOREFRONT-STYLE ADMIN PANEL ─────────────────────────────────────────────

@admin_panel_required
def admin_panel_dashboard(request):
    orders = Order.objects.select_related('user').order_by('-order_date')
    top_products = (
        OrderItem.objects.values(
            'product__productName',
            'product__productBrand__ProductBrand',
        )
        .annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum(F('price') * F('quantity')),
        )
        .order_by('-total_qty')[:5]
    )
    monthly_orders = (
        Order.objects.filter(
            order_date__gte=timezone.now() - timezone.timedelta(days=180)
        )
        .annotate(month=TruncMonth('order_date'))
        .values('month')
        .annotate(revenue=Sum('total_amount'), orders=Count('id'))
        .order_by('month')
    )
    status_counts = {
        status: Order.objects.filter(status=status).count()
        for status, _ in Order.STATUS_CHOICES
    }
    payment_counts = {
        method: Order.objects.filter(payment_method=method).count()
        for method, _ in Order.PAYMENT_CHOICES
    }
    context = {
        'total_revenue': Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0,
        'total_orders': orders.count(),
        'pending_orders': orders.filter(status='pending').count(),
        'total_users': User.objects.filter(is_staff=False, is_superuser=False).count(),
        'total_products': Product.objects.count(),
        'total_brands': ProductBrand.objects.count(),
        'recent_orders': orders[:8],
        'top_products': top_products,
        'labels': json.dumps([row['month'].strftime('%b %Y') for row in monthly_orders]),
        'revenue_data': json.dumps([float(row['revenue'] or 0) for row in monthly_orders]),
        'order_data': json.dumps([row['orders'] for row in monthly_orders]),
        'status_counts': json.dumps(status_counts),
        'payment_counts': json.dumps(payment_counts),
    }
    return render(request, 'manager/dashboard.html', context)


@admin_panel_required
def admin_panel_products(request):
    products = Product.objects.select_related('productBrand').order_by('productName')
    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(productName__icontains=query)
    return render(request, 'manager/products.html', {
        'products': products,
        'query': query,
    })


@admin_panel_required
def admin_panel_product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        product = form.save()
        messages.success(request, f'{product.productName} was added.')
        return redirect('admin_panel_products')
    return render(request, 'manager/product_form.html', {
        'form': form,
        'page_title': 'Add product',
    })


@admin_panel_required
def admin_panel_product_update(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{product.productName} was updated.')
        return redirect('admin_panel_products')
    return render(request, 'manager/product_form.html', {
        'form': form,
        'page_title': 'Edit product',
        'product': product,
    })


@admin_panel_required
@require_POST
def admin_panel_product_delete(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if OrderItem.objects.filter(product=product).exists():
        messages.error(
            request,
            'This product appears in an order and cannot be deleted.',
        )
        return redirect('admin_panel_products')
    name = product.productName
    product.delete()
    messages.success(request, f'{name} was deleted.')
    return redirect('admin_panel_products')


@admin_panel_required
def admin_panel_brands(request):
    brands = ProductBrand.objects.annotate(product_count=Count('product')).order_by('ProductBrand')
    return render(request, 'manager/brands.html', {'brands': brands})


@admin_panel_required
def admin_panel_brand_create(request):
    form = ProductBrandForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Product brand was added.')
        return redirect('admin_panel_brands')
    return render(request, 'manager/brand_form.html', {
        'form': form,
        'page_title': 'Add brand',
    })


@admin_panel_required
def admin_panel_brand_update(request, brand_id):
    brand = get_object_or_404(ProductBrand, pk=brand_id)
    form = ProductBrandForm(request.POST or None, instance=brand)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Product brand was updated.')
        return redirect('admin_panel_brands')
    return render(request, 'manager/brand_form.html', {
        'form': form,
        'page_title': 'Edit brand',
        'brand': brand,
    })


@admin_panel_required
@require_POST
def admin_panel_brand_delete(request, brand_id):
    brand = get_object_or_404(ProductBrand, pk=brand_id)
    if brand.product_set.exists():
        messages.error(request, 'Move or delete this brand’s products before deleting it.')
    else:
        brand.delete()
        messages.success(request, 'Product brand was deleted.')
    return redirect('admin_panel_brands')


@admin_panel_required
def admin_panel_orders(request):
    orders = Order.objects.select_related('user').prefetch_related('items').order_by('-order_date')
    status = request.GET.get('status', '')
    query = request.GET.get('q', '').strip()
    if status in dict(Order.STATUS_CHOICES):
        orders = orders.filter(status=status)
    if query:
        orders = orders.filter(
            Q(user__username__icontains=query)
            | Q(user__email__icontains=query)
            | Q(phone__icontains=query)
        )
    return render(request, 'manager/orders.html', {
        'orders': orders,
        'selected_status': status,
        'query': query,
        'status_choices': Order.STATUS_CHOICES,
    })


@admin_panel_required
def admin_panel_order_update(request, order_id):
    order = get_object_or_404(Order.objects.select_related('user'), pk=order_id)
    form = OrderStatusForm(request.POST or None, instance=order)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Order INV-{order.id:05d} status was updated.')
        return redirect('admin_panel_orders')
    return render(request, 'manager/order_update.html', {
        'order': order,
        'form': form,
    })
