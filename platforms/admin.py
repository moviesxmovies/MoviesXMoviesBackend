from django.contrib import admin

from .models import Platform
from unfold.admin import ModelAdmin


@admin.register(Platform)
class PlatformAdmin(ModelAdmin):
    list_display = ['name', 'url']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    exclude = ['deleted_at']
