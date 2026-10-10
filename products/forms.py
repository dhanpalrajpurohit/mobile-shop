from django import forms

from .models import Order, Product, ProductBrand


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "productName",
            "productBrand",
            "productPrice",
            "stock",
            "productSpecf",
            "productDesc",
            "productImage",
        )
        widgets = {
            "productDesc": forms.Textarea(attrs={"rows": 4}),
            "productSpecf": forms.TextInput(),
        }


class ProductBrandForm(forms.ModelForm):
    class Meta:
        model = ProductBrand
        fields = ("ProductBrand",)


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ("status",)
