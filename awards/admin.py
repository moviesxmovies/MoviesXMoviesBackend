from django.contrib import admin
from .models import Award
@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "category", "icon", "date", "created_at"]
    prepopulated_fields = {"slug": ("name",)}