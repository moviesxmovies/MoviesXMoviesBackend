from django.contrib import admin
from .models import Movie

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "synopsis", "release_date", "cover"]
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("directors", "actors", "genres", "platforms")