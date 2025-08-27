
from django.contrib import admin
from django.urls import path, include
from posts import views as post_views
from social_auth import views as auth_views
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', post_views.dashboard, name='dashboard'),
    path('posts/', include('posts.urls')),

    # Facebook
    path('connect/facebook/', auth_views.connect_facebook, name='facebook_connect'),
    path('callback/facebook/', auth_views.facebook_callback, name='facebook_callback'),
    path('post/facebook/', post_views.post_to_facebook, name='post_to_facebook'),

    # Instagram
    path('connect/instagram/', auth_views.connect_instagram, name='instagram_connect'),
    path('callback/instagram/', auth_views.instagram_callback, name='instagram_callback'),
    path('post/instagram/', post_views.post_to_instagram, name='post_to_instagram'),

    # LinkedIn
    path('connect/linkedin/', auth_views.connect_linkedin, name='linkedin_connect'),
    path('callback/linkedin/', auth_views.linkedin_callback, name='linkedin_callback'),
    path('post/linkedin/', post_views.post_to_linkedin, name='post_to_linkedin'),

    path('privacy-policy/', TemplateView.as_view(template_name="privacy_policy.html"), name='privacy_policy'),

]
