from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_positive', 'user', 'movie']
    search_fields = ['title']
    exclude = ['deleted_at']
    list_filter = ['is_positive']
    autocomplete_fields = ['user', 'movie']