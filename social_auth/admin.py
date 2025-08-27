from django.contrib import admin
from .models import SocialAccount

@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "account_id", "created")