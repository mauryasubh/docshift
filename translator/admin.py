from django.contrib import admin
from .models import TranslationJob

@admin.register(TranslationJob)
class TranslationJobAdmin(admin.ModelAdmin):
    list_display  = ('id', 'original_name', 'source_lang', 'target_lang', 'status', 'char_count', 'created_at')
    list_filter   = ('status', 'source_lang', 'target_lang')
    readonly_fields = ('id', 'created_at', 'expires_at', 'char_count')
    ordering      = ('-created_at',)
