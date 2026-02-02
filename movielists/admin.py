from django.contrib import admin
from .models import MovieList

@admin.register(MovieList)
class MovieListAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "description", "privacity", "user"]
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ("movies", "user")