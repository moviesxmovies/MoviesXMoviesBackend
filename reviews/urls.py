from django.urls import path

from . import views

app_name = 'reviews'

urlpatterns = [
    path('<review:review>/', views.review_wrapper, name='movie-reviews'),
    path(
        '<review:review>/reactions/', views.reaction_review_wrapper, name='reaction-review-wrapper'
    ),  # TODO: Get gets reactions, post add a reaction
    path(
        '<review:review>/comments/', views.comment_wrapper, name='comment-wrapper'
    ),  # TODO: Create comment on post, get comments on get
    path(
        '<review:review>/comments/<comment:comment>/',
        views.comment_wrapper_with_id,
        name='comment-wrapper',
    ),  # TODO: Edit comment on PUT, reply comment on post, delete comment on delete
    path(
        '<review:review>/comments/<comment:comment>/reactions/',
        views.reaction_comment_wrapper,
        name='reaction-comment-wrapper',
    ),  # TODO: Create comment on post, get comments on get
]


# Get reactiomns retur the number of reaction per type, and which type and ids reaction do u have
