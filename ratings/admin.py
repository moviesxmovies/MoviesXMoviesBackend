from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Rating


@admin.register(Rating)
class RatingAdmin(ModelAdmin):
    list_display = ['rating', 'user', 'movie']
    exclude = ['deleted_at']
    list_filter = ['rating']
    autocomplete_fields = ['user', 'movie']
