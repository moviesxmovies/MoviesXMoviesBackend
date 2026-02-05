from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ['bio', 'boarded', 'verified']}),
    )

