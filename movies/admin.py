from django.contrib import admin
from .models import Movie

class MovieTranslationInline(admin.TabularInline):
    model = Movie.MovieTranslation
    extra = 0 
    fields = ['language', 'title', 'synopsis', 'image']
    readonly_fields = ['language']

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    exclude = ['deleted_at']
    list_display = ['title', 'release_date']
    search_fields = ['title']
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ['platforms']
    filter_horizontal = ('directors', 'actors', 'genres', 'platforms', 'awards')
    inlines = [MovieTranslationInline]