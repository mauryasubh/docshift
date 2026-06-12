from django.contrib import admin
from django.utils import timezone
from datetime import timedelta
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'api_key', 'plan_tier', 'api_calls_used_this_month', 'plan_start_date', 'plan_expiry_date', 'last_quota_reset')
    list_filter = ('plan_tier',)
    search_fields = ('user__username', 'user__email', 'api_key')
    readonly_fields = ('api_key',)
    ordering = ('-user__date_joined',)
    actions = ['activate_corporate', 'deactivate_to_free']

    @admin.action(description="✅ Activate Corporate Plan (1 Year)")
    def activate_corporate(self, request, queryset):
        now = timezone.now()
        count = 0
        from converter.email_utils import send_plan_confirmation_email
        for profile in queryset:
            profile.plan_tier = 'Corporate'
            profile.plan_start_date = now
            profile.plan_expiry_date = now + timedelta(days=365)
            profile.last_quota_reset = now
            profile.api_calls_used_this_month = 0
            profile.save()
            # Send confirmation email
            send_plan_confirmation_email(profile.user, 'Corporate', plan_expiry_date=profile.plan_expiry_date)
            count += 1
        self.message_user(request, f"✅ {count} profile(s) upgraded to Corporate (expires {(now + timedelta(days=365)).strftime('%Y-%m-%d')}) and confirmation emails sent.")

    @admin.action(description="❌ Deactivate → Free Plan")
    def deactivate_to_free(self, request, queryset):
        updated = queryset.update(
            plan_tier='Free',
            plan_start_date=None,
            plan_expiry_date=None,
            last_quota_reset=None,
            api_calls_used_this_month=0,
            stripe_subscription_id='',
            razorpay_subscription_id='',
        )
        self.message_user(request, f"❌ {updated} profile(s) reverted to Free.")
