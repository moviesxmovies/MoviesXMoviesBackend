from django.contrib import admin

from .models import Comment, Reaction, Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['pk', 'title', 'is_positive', 'user', 'movie']
    search_fields = ['title']
    exclude = ['deleted_at']
    list_filter = ['is_positive']
    autocomplete_fields = ['user', 'movie']

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ['pk', 'user', 'emoji', 'created_at']
    search_fields = ['user__username']
    exclude = ['deleted_at']
    list_filter = ['emoji']
    autocomplete_fields = ['user']

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['pk','user', 'review', 'created_at','reply_comment']
    search_fields = ['user__username', 'review__title']
    exclude = ['deleted_at']
    autocomplete_fields = ['user', 'review']