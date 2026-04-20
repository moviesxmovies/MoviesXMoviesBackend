from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import FriendRequest, FriendShip, User

admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(ModelAdmin):
    pass


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    model = User

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    fieldsets = BaseUserAdmin.fieldsets + (
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
                    'picture',
                ]
            },
        ),
        ('Contacts', {'fields': ['following_person']}),
        ('Platforms', {'fields': ['platforms']}),
    )

    list_display = ['username', 'boarded', 'verified']
    list_filter = ['boarded', 'verified']
    search_fields = ['username', 'email']
    filter_horizontal = BaseUserAdmin.filter_horizontal + (
        'following_person',
        'platforms',
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('username', 'email', 'password'),
            },
        ),
    )


@admin.register(FriendShip)
class FriendShipAdmin(ModelAdmin):
    list_display = ['user1', 'user2', 'created_at']
    search_fields = ['user1__username', 'user2__username']
    autocomplete_fields = ['user1', 'user2']


@admin.register(FriendRequest)
class FriendRequestAdmin(ModelAdmin):
    list_display = ['from_user', 'to_user', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['from_user__username', 'to_user__username']
    autocomplete_fields = ['from_user', 'to_user']
