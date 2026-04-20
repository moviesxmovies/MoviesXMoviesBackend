from django.contrib import admin

from .models import Genre
from unfold.admin import ModelAdmin,TabularInline

class GenreTranslationInline(TabularInline):
    model = Genre.GenreTranslation
    extra = 0 
    fields = ['language', 'name']
    readonly_fields = ['language']

@admin.register(Genre)
class GenreAdmin(ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    exclude = ['deleted_at']
    inlines = [GenreTranslationInline]
