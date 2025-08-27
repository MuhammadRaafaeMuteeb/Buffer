
from django.urls import path
from . import views

urlpatterns = [
    path('connect/facebook/', views.connect_facebook, name='facebook_connect'),
    path('callback/facebook/', views.facebook_callback, name='facebook_callback'),

    path('connect/instagram/', views.connect_instagram, name='instagram_connect'),
    path('callback/instagram/', views.instagram_callback, name='instagram_callback'),

    path('connect/linkedin/', views.connect_linkedin, name='linkedin_connect'),
    path('callback/linkedin/', views.linkedin_callback, name='linkedin_callback'),
]
