from django.contrib import admin

from .models import Comment, Reaction, Review
from unfold.admin import ModelAdmin


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ['pk', 'title', 'is_positive', 'user', 'movie']
    search_fields = ['title']
    exclude = ['deleted_at']
    list_filter = ['is_positive']
    autocomplete_fields = ['user', 'movie']

@admin.register(Reaction)
class ReactionAdmin(ModelAdmin):
    list_display = ['pk', 'user', 'emoji', 'created_at']
    search_fields = ['user__username']
    exclude = ['deleted_at']
    list_filter = ['emoji']
    autocomplete_fields = ['user']

@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ['pk','user', 'review', 'created_at','reply_comment']
    search_fields = ['user__username', 'review__title']
    exclude = ['deleted_at']
    autocomplete_fields = ['user', 'review']