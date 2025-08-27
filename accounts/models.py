from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    meta_access_token = models.TextField(blank=True, null=True)
    linkedin_access_token = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

# ✅ This actually connects the signal to User
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()