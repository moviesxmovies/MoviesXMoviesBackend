from django.contrib import admin
from .models import Platform

@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    pass