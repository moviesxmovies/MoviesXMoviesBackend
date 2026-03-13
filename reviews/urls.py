from django.urls import path

from . import views

app_name = 'reviews'

urlpatterns = [
    path('<review:review>/', views.review_wrapper, name='movie-reviews'),
    path(
        '<review:review>/reactions/', views.reaction_review_wrapper, name='reaction-review-wrapper'
    ),
    path(
        '<review:review>/reactions/<reaction:reaction>/',
        views.delete_review_reaction,
        name='delete-reaction-review',
    ),
    path('<review:review>/comments/', views.comment_wrapper, name='comment-wrapper'),
    path(
        '<review:review>/comments/<comment:comment>/',
        views.comment_wrapper_with_id,
        name='comment-wrapper-with-id',
    ),
    path(
        '<review:review>/comments/<comment:comment>/replies/',
        views.reply_wrapper,
        name='reply-comment-wrapper',
    ),
    path(
        '<review:review>/comments/<comment:comment>/reactions/',
        views.reaction_comment_wrapper,
        name='reaction-comment-wrapper',
    ),
    path(
        '<review:review>/comments/<comment:comment>/reactions/<reaction:reaction>/',
        views.delete_reaction_comment,
        name='delete-reaction-comment',
    ),
]
