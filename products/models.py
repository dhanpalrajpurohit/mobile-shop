from django.db import models
from PIL import Image
from django.urls import reverse
from django.contrib.auth.models import User


# this is model but we can say that it's a table(ProductBrand) with ProductBrand column.
class ProductBrand(models.Model):
    ProductBrand = models.CharField(max_length=30)

    def __str__(self):
        return self.ProductBrand


# this class for create Product table in database.
class Product(models.Model):
    productName = models.TextField(max_length=30)
    productSpecf = models.TextField(max_length=100, null=True)
    productDesc = models.TextField(max_length=400)
    productImage = models.ImageField(upload_to='product_pics/')
    productPrice = models.IntegerField()
    productBrand = models.ForeignKey(ProductBrand, on_delete=models.CASCADE, default=1)
    stock = models.IntegerField(default=10)

    def __str__(self):
        return self.productName

    def get_absolute_url(self):
        return reverse('product-detail', kwargs={'productName': self.productName})

    def average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return round(sum([r.rating for r in reviews]) / len(reviews), 1)
        return 0


class Review(models.Model):
    RATING_CHOICES = [(i, i) for i in range(1, 6)]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=100)
    body = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')

    def __str__(self):
        return f'{self.user.username} - {self.product.productName} ({self.rating}star)'


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f'{self.user.username} - {self.product.productName} x{self.quantity}'

    def subtotal(self):
        return self.product.productPrice * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('online', 'Online Payment'),
        ('card', 'Credit/Debit Card'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cod')
    payment_status = models.CharField(max_length=20, default='pending')
    shipping_address = models.TextField()
    phone = models.CharField(max_length=15)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Order #{self.id} by {self.user.username}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f'{self.product.productName} x{self.quantity}'
