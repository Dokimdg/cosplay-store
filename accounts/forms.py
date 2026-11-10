from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import CustomUser, UserProfile


class RegisterForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email')


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('nickname', 'phone', 'address')
        widgets = {'address': forms.Textarea(attrs={'rows': 3})}
