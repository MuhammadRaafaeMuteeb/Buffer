from django.db import models
from django.contrib.auth.models import User

class Post(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="posts"  # ✅ allows request.user.posts.all()
    )
    text = models.TextField()
    image_url = models.URLField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    platforms = models.CharField(max_length=255, blank=True, null=True)  # ✅ new field


    # 🔗 Separate post URLs for each platform
    facebook_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)

    
    def __str__(self):
        return f"{self.user.username} - {self.created.strftime('%Y-%m-%d %H:%M')}"