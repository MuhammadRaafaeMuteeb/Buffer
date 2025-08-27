from django.db import models
from django.contrib.auth.models import User

class SocialAccount(models.Model):
    PROVIDER_CHOICES = [('meta','Meta'),('linkedin','LinkedIn')]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    account_id = models.CharField(max_length=200, blank=True, null=True)
    access_token = models.TextField()
    extra = models.JSONField(default=dict, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.provider}"
