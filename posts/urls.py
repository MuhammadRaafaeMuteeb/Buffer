from django.urls import path
from . import views
urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path('create/', views.new_post, name='create_post'),
    path("accounts/manage/", views.manage_accounts, name="manage_accounts"),
    path("accounts/disconnect/<str:platform>/", views.disconnect_account, name="disconnect_account"),
    #path('create/', views.create_post, name='create_post'),
    #path('publish/<int:post_id>/', views.publish_post, name='publish_post'),
]