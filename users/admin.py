from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User

    fieldsets = UserAdmin.fieldsets + (
        (
            None,
            {'fields': ['bio', 'boarded', 'verified', 'verification_code', 'forgot_password_code', 'preferred_language']},
        ),
        ('Follow', {'fields': ['following_person', 'following']}),
        ('Platforms', {'fields': ['platforms']}),
    )
    list_display = ['username', 'boarded', 'verified']
    list_filter = ['boarded', 'verified']
    search_fields = ['username', 'email']
    filter_horizontal = UserAdmin.filter_horizontal + ('following_person', 'following', 'platforms')
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('username', 'email', 'usable_password', 'password1', 'password2'),
            },
        ),
    )
