from django.urls import path

from . import views

app_name = 'reviews'

urlpatterns = [
    path('<review:review>/', views.review_wrapper, name='movie-reviews'),
    path(
        '<review:review>/reactions/', views.reaction_review_wrapper, name='reaction-review-wrapper'
    ),  # TODO: Get gets reactions, post add a reaction
    path(
        '<review:review>/reactions/<reaction:reaction>/',
        views.delete_review_reaction,
        name='delete-reaction-review',
        # TODO: Delete reaction on delete
    ),
    path(
        '<review:review>/comments/', views.comment_wrapper, name='comment-wrapper'
    ),  # TODO: Create comment on post, get comments pagination on get
    path(
        '<review:review>/comments/<comment:comment>/',
        views.comment_wrapper_with_id,
        name='comment-wrapper-with-id',
    ),  # TODO: Edit comment on PUT, delete comment on delete, Get on get
    path(
        '<review:review>/comments/<comment:comment>/replies/',
        views.reply_wrapper,
        name='reply-comment-wrapper',
        # TODO: Create reply on post, get replies pagination on get
    ),
    path(
        '<review:review>/comments/<comment:comment>/reactions/',
        views.reaction_comment_wrapper,
        name='reaction-comment-wrapper',
    ),  # TODO: Create reaction on post, get reactions on get
    path(
        '<review:review>/comments/<comment:comment>/reactions/<reaction:reaction>/',
        views.delete_reaction_comment,
        name='delete-reaction-comment',
        # TODO: Delete reaction on delete
    ),
]


# Get reactiomns retur the number of reaction per type, and which type and ids reaction do u have
