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
    list_display = ('name', 'email', 'company', 'created_at')
    search_fields = ('name', 'email', 'company')
    ordering = ('-created_at',)
