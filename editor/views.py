"""
editor/views.py
---------------
Views:
  editor_home        GET  /editor/                  → upload page
  editor_upload      POST /editor/upload/           → create session, dispatch task, redirect
  editor_session     GET  /editor/session/<id>/     → main editor UI
  editor_status_json GET  /editor/session/<id>/status/ → poll JSON for analysis progress
  editor_save        POST /editor/session/<id>/save/   → receive edits JSON, dispatch save task
  editor_download    GET  /editor/session/<id>/download/ → serve result file
  editor_page_image  GET  /editor/session/<id>/page/<n>/  → serve page PNG
"""

import os
import json
from pathlib import Path

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone

from .models import EditorSession
from .tasks import analyse_pdf_task, save_edits_task


MAX_UPLOAD_SIZE = getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024)   # 50 MB


# ──────────────────────────────────────────────────────────────────────────────
#  Home / Upload
# ──────────────────────────────────────────────────────────────────────────────

def editor_home(request):
    """Upload page — drag & drop a PDF to start editing."""
    return render(request, 'editor/upload.html')


@require_http_methods(["POST"])
def editor_upload(request):
    """
    Receive uploaded PDF, create EditorSession, dispatch analyse_pdf_task.
    Redirects to the editor session page.
    """
    uploaded = request.FILES.get('file')

    if not uploaded:
        return render(request, 'editor/upload.html', {'error': 'No file uploaded.'})

    # Basic validation
    ext = Path(uploaded.name).suffix.lower()
    if ext != '.pdf':
        return render(request, 'editor/upload.html', {'error': 'Only PDF files are supported.'})

    if uploaded.size > MAX_UPLOAD_SIZE:
        mb = MAX_UPLOAD_SIZE // (1024 * 1024)
        return render(request, 'editor/upload.html', {'error': f'File too large. Max {mb} MB.'})

    # Quick magic-bytes check
    uploaded.seek(0)
    header = uploaded.read(4)
    uploaded.seek(0)
    if header != b'%PDF':
        return render(request, 'editor/upload.html', {'error': 'File does not appear to be a valid PDF.'})

    # Create session
    is_guest = not request.user.is_authenticated
    session = EditorSession(
        user=request.user if not is_guest else None,
        is_guest=is_guest,
        original_file=uploaded,
        original_name=uploaded.name,
        original_size=uploaded.size,
    )
    session.save()

    # Track in session for guest users (same pattern as converter)
    if is_guest:
        ids = request.session.get('editor_sessions', [])
        ids.insert(0, str(session.id))
        request.session['editor_sessions'] = ids[:20]

    # Dispatch Celery analysis task
    try:
        analyse_pdf_task.apply_async(args=[str(session.id)])
    except Exception as e:
        session.status = 'failed'
        session.error_message = f'Service unavailable: {str(e)}. Please check background worker connection.'
        session.save(update_fields=['status', 'error_message'])

    return redirect('editor_session', session_id=session.id)


# ──────────────────────────────────────────────────────────────────────────────
#  Editor UI
# ──────────────────────────────────────────────────────────────────────────────

def editor_session(request, session_id):
    """Main editor page — shows the PDF with interactive overlay."""
    session = get_object_or_404(EditorSession, id=session_id)

    # Build list of page image URLs (only available once status='ready')
    page_urls = []
    if session.status == 'ready' and session.page_count > 0:
        page_urls = [session.page_image_url(i + 1) for i in range(session.page_count)]

    # Extract page dimensions from blocks_json meta entry
    page_dims = []
    if session.blocks_json:
        first = session.blocks_json[0] if session.blocks_json else {}
        if first.get('type') == 'meta':
            page_dims = first.get('page_dimensions', [])

    # Separate actual blocks from meta
    content_blocks = [b for b in session.blocks_json if b.get('type') != 'meta']

    return render(request, 'editor/editor.html', {
        'session':        session,
        'page_urls':      json.dumps(page_urls),
        'page_dims':      json.dumps(page_dims),
        'blocks_json':    json.dumps(content_blocks),
        'images_json':    json.dumps(session.images_json),
        'page_count':     session.page_count,
        'expiry_seconds': session.seconds_until_expiry(),
    })


# ──────────────────────────────────────────────────────────────────────────────
#  Status polling (AJAX)
# ──────────────────────────────────────────────────────────────────────────────

def editor_status_json(request, session_id):
    """JSON endpoint polled by the frontend while analysis is running."""
    session = get_object_or_404(EditorSession, id=session_id)

    progress_map = {
        'analysing': 40,
        'ready':     100,
        'saving':    70,
        'saved':     100,
        'failed':    100,
    }

    page_urls = []
    if session.status == 'ready' and session.page_count > 0:
        page_urls = [session.page_image_url(i + 1) for i in range(session.page_count)]

    page_dims = []
    content_blocks = []
    if session.status == 'ready' and session.blocks_json:
        first = session.blocks_json[0] if session.blocks_json else {}
        if first.get('type') == 'meta':
            page_dims = first.get('page_dimensions', [])
        content_blocks = [b for b in session.blocks_json if b.get('type') != 'meta']

    return JsonResponse({
        'status':         session.status,
        'progress':       progress_map.get(session.status, 0),
        'pdf_type':       session.pdf_type,
        'page_count':     session.page_count,
        'block_count':    len(content_blocks),
        'image_count':    len(session.images_json),
        'page_urls':      page_urls,
        'page_dims':      page_dims,
        'blocks':         content_blocks,
        'images':         session.images_json,
        'error_message':  session.error_message if session.status == 'failed' else None,
        'expiry_seconds': session.seconds_until_expiry(),
        'download_url':   f'/editor/session/{session_id}/download/'
                          if session.status == 'saved' and session.result_file else None,
    })


# ──────────────────────────────────────────────────────────────────────────────
#  Save edits (AJAX POST)
# ──────────────────────────────────────────────────────────────────────────────

@require_http_methods(["POST"])
def editor_save(request, session_id):
    """
    Receive edits payload as JSON body, dispatch save_edits_task.
    Returns JSON with task status.
    """
    session = get_object_or_404(EditorSession, id=session_id)

    if session.status not in ('ready', 'saved'):
        return JsonResponse({'error': 'Session not ready for saving.'}, status=400)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

    # Validate payload has at least one of the expected keys
    has_work = (
        payload.get('text_edits') or
        payload.get('image_actions') or
        payload.get('annotations')
    )
    if not has_work:
        return JsonResponse({'error': 'No edits to save.'}, status=400)

    session.status = 'saving'
    session.save(update_fields=['status'])

    try:
        save_edits_task.apply_async(args=[str(session_id), payload])
    except Exception as e:
        return JsonResponse({'error': f'Service unavailable: {str(e)}. Please check background worker connection.'}, status=503)

    return JsonResponse({'status': 'saving', 'message': 'Save started.'})


# ──────────────────────────────────────────────────────────────────────────────
#  Download result
# ──────────────────────────────────────────────────────────────────────────────

def editor_download(request, session_id):
    """Serve the saved/edited PDF as an attachment."""
    session = get_object_or_404(EditorSession, id=session_id)

    if session.status != 'saved' or not session.result_file:
        raise Http404("Edited file not ready.")

    file_path = session.result_file.path
    if not os.path.exists(file_path):
        raise Http404("File not found on disk.")

    filename = Path(file_path).name
    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)


# ──────────────────────────────────────────────────────────────────────────────
#  Serve page images
# ──────────────────────────────────────────────────────────────────────────────

def editor_page_image(request, session_id, page_number):
    """
    Serve a single page PNG for the editor viewer.
    page_number is 1-indexed.
    """
    session = get_object_or_404(EditorSession, id=session_id)
    from django.core.files.storage import default_storage
    from django.shortcuts import redirect
    
    path = f"editor_pages/{session.id}/page_{page_number}.png"
    try:
        return redirect(default_storage.url(path))
    except Exception:
        raise Http404("Page image not accessible")
