from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import SignupForm, LoginForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.forms import PasswordResetForm
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model




def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            # print("کاربر ثبت شد", user)
            return redirect("login")
    else:
        # print("خطای فرم", form.errors)
        form = SignupForm()
    return render(request,"registrations/signup.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            phone = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=phone, password=password)
            if user is not None:
                login(request, user)
                return redirect("home")
            else:
                messages.error(request, "نام کاربری یا رمز عبور اشتباه است")
    else:
        form = LoginForm()
    return render(request, "registrations/login.html", {"form": form})


def logout_view(request):
    if request.user.is_authenticated:
        phone_number = request.user.phone  # دریافت شماره تلفن از مدل کاربر
        messages.success(request, f"کاربر با شماره {phone_number} با موفقیت خارج شد.")
        logout(request)
    return redirect("login")



class CustomPasswordResetView(FormView):
    template_name = "auth/password_reset_form.html"
    form_class = PasswordResetForm
    success_url = reverse_lazy("auth/password_reset_done")

    def form_valid(self, form):
        User = get_user_model()
        user = User.objects.filter(email=form.cleaned_data["email"]).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = f"http://127.0.0.1:8000/reset/{uid}/{token}/"

            print(f"Password Reset Link: {reset_link}")  # ✅ نمایش لینک در سرور

            return self.render_to_response(self.get_context_data(reset_link=reset_link))

        return super().form_valid(form)


