from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ['bio', 'boarded', 'verified']}),
    )
    list_display = ['username', 'boarded', 'verified']
    list_filter = ['boarded', 'verified']
    search_fields = ['username', 'email']
    filter_horizontal = UserAdmin.filter_horizontal + ('following_person', 'following', 'platforms')

