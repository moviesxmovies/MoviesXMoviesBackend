from django.contrib import admin
from .models import MovieList

@admin.register(MovieList)
class MovieListAdmin(admin.ModelAdmin):
    list_display = ['name', 'privacity', 'user']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    exclude = ['deleted_at']
    list_filter = ['privacity']
    autocomplete_fields = ['user']
    filter_horizontal = ['movies']