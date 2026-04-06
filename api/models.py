import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    PLAN_CHOICES = (
        ('Free', 'Free'),
        ('Developer', 'Developer'),
        ('Corporate', 'Corporate'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='api_profile')
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    webhook_url = models.URLField(max_length=500, blank=True, null=True)
    
    plan_tier = models.CharField(max_length=20, choices=PLAN_CHOICES, default='Free')
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    api_calls_used_this_month = models.IntegerField(default=0)
    
    plan_start_date = models.DateTimeField(null=True, blank=True)
    plan_expiry_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
        
    def is_plan_active(self):
        from django.utils import timezone
        if self.plan_tier == 'Free':
            return True
        if not self.plan_expiry_date:
            return False
        return timezone.now() < self.plan_expiry_date

    def get_monthly_quota(self):
        if self.plan_tier == 'Corporate':
            return 50000
        elif self.plan_tier == 'Developer':
            return 5000
        return 0  # Free tier
        
    def can_make_api_call(self):
        quota = self.get_monthly_quota()
        if quota <= 0:
            return False
        return self.api_calls_used_this_month < quota

# Auto-create Profiles for new users
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.api_profile.save()
    except Profile.DoesNotExist:
        Profile.objects.create(user=instance)
