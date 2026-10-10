from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(ImportExportModelAdmin):
    list_display = ('image_thumb', 'user', 'email_display', 'full_name_display')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    list_select_related = ('user',)
    list_per_page = 25

    def image_thumb(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html(
                '<img src="{}" style="width: 48px; height: 48px; object-fit: cover; border-radius: 50%; border: 2px solid #3b82f6;">',
                obj.image.url
            )
        # Default placeholder if no image
        return format_html(
            '<div style="width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #3b82f6, #8b5cf6); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 20px;">{}</div>',
            obj.user.username[0].upper() if obj.user.username else '?'
        )
    image_thumb.short_description = 'Avatar'

    def email_display(self, obj):
        return obj.user.email
    email_display.short_description = 'Email'
    email_display.admin_order_field = 'user__email'

    def full_name_display(self, obj):
        name = obj.user.get_full_name()
        if name:
            return format_html('<strong>{}</strong>', name)
        return format_html('<em style="color:#9ca3af">{}</em>', '—')
    full_name_display.short_description = 'Full Name'
    full_name_display.admin_order_field = 'user__first_name'