from .forms  import CustomerSignUp
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.urls import reverse
from .decorators import client_required
from .forms import ProfileUpdateForm,UserUpdateForm
from .forms import ClientAuthenticationForm, AdminPanelAuthenticationForm
from .models import Profile
# Create your views here.


class RoleLoginView(LoginView):
    redirect_authenticated_user = True

    def get_success_url(self):
        if self.request.user.is_superuser:
            return reverse('admin:index')
        if self.request.user.is_staff:
            return reverse('admin_panel_dashboard')
        return reverse('index')


class ClientLoginView(RoleLoginView):
    authentication_form = ClientAuthenticationForm


class AdminPanelLoginView(RoleLoginView):
    authentication_form = AdminPanelAuthenticationForm


def signup(request):
    if request.method == "POST":
        form = CustomerSignUp(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, "User {} is successfully registered!!! ".format(username))
            return redirect('signin')
    else:
        form = CustomerSignUp()

    return render(request, 'signup.html', {'form': form})


def password_change_done(request):
    return render(request,'login.html')

@client_required
def profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(data=request.POST,files= request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'profile_form': profile_form,
        'user_form': user_form
    }
    return render(request, 'user_profile.html',context)
