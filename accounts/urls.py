from django.urls import path, include, reverse_lazy
from . import views as user_views
from django.contrib.auth import views as  auth_views

urlpatterns = [
    path('signup/',user_views.signup,name='signup'),
    path('login/',user_views.ClientLoginView.as_view(template_name='signin.html'),name='signin'),
    path('logout/',auth_views.LogoutView.as_view(template_name='user_logout.html'),name='logout'),
    path('profile/',user_views.profile,name='profile'),
    path('change_password/',auth_views.PasswordChangeView.as_view(success_url=reverse_lazy('accounts:password_change_done'),template_name='registration/change_password.html'),name='change_password'),
    #path('password_change_done/',auth_views.PasswordChangeDoneView.as_view(),name='change_password_done'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/',auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete')
]