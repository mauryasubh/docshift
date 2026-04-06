from django.contrib import admin
from .models import EditorSession

@admin.register(EditorSession)
class EditorSessionAdmin(admin.ModelAdmin):
    list_display   = ('id', 'original_name', 'pdf_type', 'status', 'page_count', 'is_guest', 'user', 'created_at', 'expires_at')
    list_filter    = ('status', 'pdf_type', 'is_guest')
    search_fields  = ('original_name', 'user__username')
    readonly_fields = ('id', 'created_at', 'expires_at', 'blocks_json', 'images_json')
    ordering       = ('-created_at',)
