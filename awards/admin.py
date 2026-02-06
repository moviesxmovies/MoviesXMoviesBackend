from django.contrib import admin

from .models import Award


@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'date']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    exclude = ['deleted_at']
    list_filter = ['category']
    ordering = ['date']
