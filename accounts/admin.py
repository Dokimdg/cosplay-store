from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import CustomUser, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


@admin.register(CustomUser)
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    # Поле email обов'язкове й на сторінці створення користувача в адмінці
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('email',)}),
    )
