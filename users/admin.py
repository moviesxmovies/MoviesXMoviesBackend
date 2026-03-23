from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import FriendRequest, FriendShip, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = UserAdmin.fieldsets + (
        (
            None,
            {
                'fields': [
                    'bio',
                    'boarded',
                    'verified',
                    'verification_code',
                    'forgot_password_code',
                    'preferred_language',
                ]
            },
        ),
        ('Contacts', {'fields': ['following_person']}),
        ('Platforms', {'fields': ['platforms']}),
    )
    list_display = ['username', 'boarded', 'verified']
    list_filter = ['boarded', 'verified']
    search_fields = ['username', 'email']
    filter_horizontal = UserAdmin.filter_horizontal + (
        'following_person',
        'platforms',
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('username', 'email', 'usable_password', 'password1', 'password2'),
            },
        ),
    )


@admin.register(FriendShip)
class FriendShipAdmin(admin.ModelAdmin):
    list_display = ['user1', 'user2', 'created_at']
    search_fields = ['user1__username', 'user2__username']
    autocomplete_fields = ['user1', 'user2']


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ['from_user', 'to_user', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['from_user__username', 'to_user__username']
    autocomplete_fields = ['from_user', 'to_user']
