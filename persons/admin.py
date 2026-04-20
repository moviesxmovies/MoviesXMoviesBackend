from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Person


class PersonTranslationInline(TabularInline):
    model = Person.PersonTranslation
    extra = 0
    fields = ['language', 'biography']
    readonly_fields = ['language']


@admin.register(Person)
class PersonAdmin(ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    inlines = [PersonTranslationInline]
    prepopulated_fields = {'slug': ('name',)}
    exclude = ['deleted_at']
    filter_horizontal = ['awards']
    list_filter = ['gender', 'deathday']
