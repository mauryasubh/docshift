from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'api_key', 'plan_tier', 'api_calls_used_this_month', 'plan_expiry_date')
    list_filter = ('plan_tier',)
    search_fields = ('user__username', 'user__email', 'api_key')
    ordering = ('-user__date_joined',)
