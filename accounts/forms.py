from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.forms import formset_factory

User = get_user_model()

class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['phone', 'username', 'email']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+989123456789'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام کاربری'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@gmail.com'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("این شماره تماس قبلاً ثبت شده است.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("این ایمیل قبلاً استفاده شده است.")
        return email

# class LoginForm(AuthenticationForm):
#     username = forms.CharField(label="شماره تلفن یا نام کاربری")
#     password = forms.CharField(widget=forms.PasswordInput, label="رمز عبور")
    
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="شماره همراه خود را وارد کنید",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره تلفن'})
    )
    password = forms.CharField(
        label="رمز عبور را وارد کنید",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'رمز عبور'})
    )

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'phone', 'email', 'first_name', 'last_name', 'profile_photo')


