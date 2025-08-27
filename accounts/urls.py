from django.urls import path
from . import views
urlpatterns = [
    path('signup/', views.signup, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    #path('accounts/login/', views.login_view),
]
