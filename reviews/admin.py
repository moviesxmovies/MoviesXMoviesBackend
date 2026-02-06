from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['title', 'isPositive', 'user', 'movie']
    search_fields = ['title']
    exclude = ['deleted_at']
    list_filter = ['isPositive']
    autocomplete_fields = ['user']