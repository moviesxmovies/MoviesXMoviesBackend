from django.contrib import admin

from .models import Person


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ['name', 'country']
    search_fields = ['name', 'country']
    prepopulated_fields = {'slug': ('name',)}
    exclude = ['deleted_at']
