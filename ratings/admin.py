from django.contrib import admin
from .models import Rating

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ["rating", "user", "movie"]
    raw_id_fields = ("user", "movie")