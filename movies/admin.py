from django.contrib import admin

from .models import Movie


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    exclude = ['deleted_at']
    list_display = ['title', 'release_date']
    search_fields = ['title']
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ['platforms']
    filter_horizontal = ('directors', 'actors', 'genres', 'platforms', 'awards')
