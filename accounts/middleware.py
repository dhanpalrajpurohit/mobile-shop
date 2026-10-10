from django.shortcuts import redirect


class AdminRoleBoundaryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/") and request.user.is_authenticated:
            if not request.user.is_superuser:
                if request.user.is_staff:
                    return redirect("admin_panel_dashboard")
                return redirect("index")

        return self.get_response(request)
