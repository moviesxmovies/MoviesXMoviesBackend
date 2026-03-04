from django.contrib import admin

from .models import Genre
class GenreTranslationInline(admin.TabularInline):
    model = Genre.GenreTranslation
    extra = 0 
    fields = ['language', 'name']
    readonly_fields = ['language']

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    exclude = ['deleted_at']
    inlines = [GenreTranslationInline]
