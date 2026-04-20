from django.contrib import admin

from .models import Award
from unfold.admin import ModelAdmin


@admin.register(Award)
class AwardAdmin(ModelAdmin):
    list_display = ['name', 'category', 'date']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    exclude = ['deleted_at']
    list_filter = ['category']
    ordering = ['date']
