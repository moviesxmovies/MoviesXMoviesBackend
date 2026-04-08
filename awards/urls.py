from django.urls import path


from awards import views

app_name = 'awards'

urlpatterns = [
    path('<award:award>/', views.award_detail, name='award-detail'),
]
