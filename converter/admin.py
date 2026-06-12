from django.contrib import admin
from .models import ConversionJob, SalesInquiry

@admin.register(ConversionJob)
class ConversionJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'tool', 'status', 'input_size', 'output_size', 'created_at', 'expires_at')
    list_filter = ('tool', 'status')
    search_fields = ('id', 'tool')
    readonly_fields = ('id', 'created_at', 'expires_at', 'input_size', 'output_size')
    ordering = ('-created_at',)

@admin.register(SalesInquiry)
class SalesInquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'company', 'is_contacted', 'created_at')
    list_filter = ('is_contacted',)
    search_fields = ('name', 'email', 'company')
    ordering = ('-created_at',)
    actions = ['mark_as_contacted', 'mark_as_not_contacted']

    @admin.action(description="✅ Mark as Contacted")
    def mark_as_contacted(self, request, queryset):
        updated = queryset.update(is_contacted=True)
        self.message_user(request, f"✅ {updated} inquiry(ies) marked as contacted.")

    @admin.action(description="↩️ Mark as Not Contacted")
    def mark_as_not_contacted(self, request, queryset):
        updated = queryset.update(is_contacted=False)
        self.message_user(request, f"↩️ {updated} inquiry(ies) marked as not contacted.")
