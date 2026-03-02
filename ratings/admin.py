from django.contrib import admin

from .models import Rating


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['rating', 'user', 'movie']
    exclude = ['deleted_at']
    list_filter = ['rating']
    autocomplete_fields = ['user', 'movie']
