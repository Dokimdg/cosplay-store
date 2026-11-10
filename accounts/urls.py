from django.contrib.auth import views as auth_views
from django.urls import path

from cosplay_store.security import rate_limit

from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', rate_limit('register', 5, 3600)(views.register), name='register'),
    path('login/', rate_limit('login', 10, 300)(
        auth_views.LoginView.as_view(template_name='accounts/login.html')), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
]
