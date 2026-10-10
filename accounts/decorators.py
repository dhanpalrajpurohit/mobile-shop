from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse


def admin_panel_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                login_url=reverse("admin_panel_login"),
            )
        if user.is_superuser:
            return redirect("admin:index")
        if not user.is_active or not user.is_staff or user.is_superuser:
            return HttpResponseForbidden("Admin access is required.")
        return view_func(request, *args, **kwargs)

    return wrapped_view


def client_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                login_url=reverse("signin"),
            )
        if user.is_superuser:
            return redirect("admin:index")
        if not user.is_active:
            return HttpResponseForbidden("An active customer account is required.")
        return view_func(request, *args, **kwargs)

    return wrapped_view
