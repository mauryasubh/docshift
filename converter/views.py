import os, json, csv
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse, Http404, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.core.paginator import Paginator

from .models import ConversionJob, UserProfile
from .forms import (
    UploadForm, SplitPDFForm, ResizeImageForm,
    CompressPDFForm, PDFToImagesForm, PNGToJPGForm,
    PasswordProtectForm, UnlockPDFForm, RotatePDFForm,
    WatermarkPDFForm, PageNumbersForm,
    EditMetadataForm, CropPDFForm,
)
from .utils import validate_file, human_readable_size


# ─────────────────────────────────────────────────────────────
#  Tool registry
# ─────────────────────────────────────────────────────────────
TOOL_CONFIG = {
    # ── PDF Tools ────────────────────────────────────────────
    'compress_pdf':     {'name': 'Compress PDF',        'icon': '🗜️',  'category': 'pdf',
                         'description': 'Reduce PDF file size with three quality levels.',
                         'accept': '.pdf', 'form': CompressPDFForm, 'multi': False,
                         'tips': 'Extreme compression reduces quality significantly. Recommended gives the best file size to visual quality ratio.'},
    'merge_pdf':        {'name': 'Merge PDFs',          'icon': '🔗',  'category': 'pdf',
                         'description': 'Combine multiple PDFs into one — drag to reorder.',
                         'accept': '.pdf', 'form': UploadForm, 'multi': True,
                         'tips': 'You can drag and drop the uploaded file pills here to change the final merged order.'},
    'split_pdf':        {'name': 'Split PDF',           'icon': '✂️',  'category': 'pdf',
                         'description': 'Extract specific page ranges from a PDF.',
                         'accept': '.pdf', 'form': SplitPDFForm, 'multi': False},
    'pdf_to_images':    {'name': 'PDF to Images',       'icon': '🖼️',  'category': 'pdf',
                         'description': 'Convert PDF pages to PNG, JPEG or WebP images.',
                         'accept': '.pdf', 'form': PDFToImagesForm, 'multi': False},
    'pdf_to_word':      {'name': 'PDF to Word',         'icon': '📝',  'category': 'pdf',
                         'description': 'Convert PDF documents to editable Word (.docx) format.',
                         'accept': '.pdf', 'form': UploadForm, 'multi': False},
    'pdf_to_excel':     {'name': 'PDF to Excel',        'icon': '📊',  'category': 'pdf',
                         'description': 'Extract tables and data from PDF into Excel (.xlsx).',
                         'accept': '.pdf', 'form': UploadForm, 'multi': False},
    'pdf_to_pptx':      {'name': 'PDF to PowerPoint',   'icon': '📑',  'category': 'pdf',
                         'description': 'Convert each PDF page into a PowerPoint slide.',
                         'accept': '.pdf', 'form': UploadForm, 'multi': False},
    'extract_text':     {'name': 'Extract Text',        'icon': '📋',  'category': 'pdf',
                         'description': 'Pull all text out of a PDF into a .txt file.',
                         'accept': '.pdf', 'form': UploadForm, 'multi': False,
                         'tips': 'This only extracts native text layers. If your PDF is a scanned image, use the OCR tool instead.'},
    'extract_images':   {'name': 'Extract Images',      'icon': '🗂️',  'category': 'pdf',
                         'description': 'Save every embedded image from a PDF as a .zip.',
                         'accept': '.pdf', 'form': UploadForm, 'multi': False},
    'ocr_pdf':          {'name': 'OCR — Searchable PDF','icon': '🔍',  'category': 'pdf',
                         'description': 'Make a scanned PDF searchable and copy-pasteable.',
                         'accept': '.pdf', 'form': UploadForm, 'multi': False,
                         'tips': 'OCR can take a while to process. You can safely close this page after uploading and check your dashboard later.'},
    'password_protect': {'name': 'Password Protect',    'icon': '🔒',  'category': 'pdf',
                         'description': 'Add AES-256 password protection to your PDF.',
                         'accept': '.pdf', 'form': PasswordProtectForm, 'multi': False,
                         'tips': 'Make sure you remember the password! The encryption is AES-256 and we cannot recover it for you.'},
    'unlock_pdf':       {'name': 'Unlock PDF',          'icon': '🔓',  'category': 'pdf',
                         'description': 'Remove password and encryption from a protected PDF.',
                         'accept': '.pdf', 'form': UnlockPDFForm, 'multi': False},
    'rotate_pdf':       {'name': 'Rotate PDF',          'icon': '🔃',  'category': 'pdf',
                         'description': 'Rotate any page individually with a live preview.',
                         'accept': '.pdf', 'form': UploadForm, 'multi': False},
    'watermark_pdf':    {'name': 'Watermark PDF',       'icon': '💧',  'category': 'pdf',
                         'description': 'Stamp a text watermark on every page.',
                         'accept': '.pdf', 'form': WatermarkPDFForm, 'multi': False},
    'add_page_numbers': {'name': 'Add Page Numbers',    'icon': '🔢',  'category': 'pdf',
                         'description': 'Add page numbers to your PDF at any position.',
                         'accept': '.pdf', 'form': PageNumbersForm, 'multi': False},
    'edit_metadata':    {'name': 'Edit PDF Metadata',   'icon': '🏷️',  'category': 'pdf',
                         'description': 'Change title, author, subject, and keywords in a PDF.',
                         'accept': '.pdf', 'form': EditMetadataForm, 'multi': False,
                         'tips': 'Leaving a form field completely blank will keep its original value.'},
    'flatten_pdf':      {'name': 'Flatten PDF',         'icon': '🗜️',  'category': 'pdf',
                         'description': 'Make form fields and annotations permanently uneditable.',
                         'accept': '.pdf', 'form': UploadForm, 'multi': False},
    'grayscale_pdf':    {'name': 'Grayscale PDF',       'icon': '🌗',  'category': 'pdf',
                         'description': 'Convert coloured PDF pages to black and white.',
                         'accept': '.pdf', 'form': UploadForm, 'multi': False},
    'crop_pdf':         {'name': 'Crop PDF',            'icon': '✂️',  'category': 'pdf',
                         'description': 'Trim page margins of your PDF document.',
                         'accept': '.pdf', 'form': CropPDFForm, 'multi': False},


    # ── Office Tools ─────────────────────────────────────────
    'docx_to_pdf':      {'name': 'DOCX to PDF',         'icon': '📄',  'category': 'office',
                         'description': 'Convert Word documents to PDF format.',
                         'accept': '.docx', 'form': UploadForm, 'multi': False},
    'excel_to_pdf':     {'name': 'Excel to PDF',        'icon': '📈',  'category': 'office',
                         'description': 'Convert Excel spreadsheets to PDF.',
                         'accept': '.xlsx,.xls', 'form': UploadForm, 'multi': False},
    'pptx_to_pdf':      {'name': 'PowerPoint to PDF',   'icon': '📽️',  'category': 'office',
                         'description': 'Convert PowerPoint presentations to PDF.',
                         'accept': '.pptx,.ppt', 'form': UploadForm, 'multi': False},
    'txt_to_pdf':       {'name': 'TXT to PDF',          'icon': '📃',  'category': 'office',
                         'description': 'Convert plain text files into formatted PDFs.',
                         'accept': '.txt', 'form': UploadForm, 'multi': False},
    'html_to_pdf':      {'name': 'HTML to PDF',         'icon': '🌐',  'category': 'office',
                         'description': 'Convert an HTML file to a styled PDF document.',
                         'accept': '.html,.htm', 'form': UploadForm, 'multi': False},

    # ── Image Tools ──────────────────────────────────────────
    'img_to_pdf':       {'name': 'Image to PDF',        'icon': '🗒️',  'category': 'image',
                         'description': 'Wrap JPG, PNG or other images into a PDF.',
                         'accept': '.jpg,.jpeg,.png,.bmp,.tiff,.webp', 'form': UploadForm, 'multi': False},
    'jpg_to_png':       {'name': 'JPG to PNG',          'icon': '🔄',  'category': 'image',
                         'description': 'Convert JPEG images to lossless PNG format.',
                         'accept': '.jpg,.jpeg', 'form': UploadForm, 'multi': False},
    'png_to_jpg':       {'name': 'PNG to JPG',          'icon': '🔄',  'category': 'image',
                         'description': 'Convert PNG images to JPEG with adjustable quality.',
                         'accept': '.png', 'form': PNGToJPGForm, 'multi': False},
    'resize_image':     {'name': 'Resize Image',        'icon': '📐',  'category': 'image',
                         'description': 'Resize images to specific dimensions with Lanczos.',
                         'accept': '.jpg,.jpeg,.png,.bmp,.tiff,.webp', 'form': ResizeImageForm, 'multi': False},
}


# ─────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────

def _get_tasks():
    return __import__('converter.tasks', fromlist=['*'])


def _dispatch_task(tool_slug, job, extra_kwargs=None):
    tasks = _get_tasks()
    task_map = {
        # Round 1
        'compress_pdf':     tasks.compress_pdf_task,
        'merge_pdf':        tasks.merge_pdfs_task,
        'split_pdf':        tasks.split_pdf_task,
        'pdf_to_images':    tasks.pdf_to_images_task,
        'pdf_to_word':      tasks.pdf_to_word_task,
        'docx_to_pdf':      tasks.docx_to_pdf_task,
        'txt_to_pdf':       tasks.txt_to_pdf_task,
        'img_to_pdf':       tasks.img_to_pdf_task,
        'jpg_to_png':       tasks.jpg_to_png_task,
        'png_to_jpg':       tasks.png_to_jpg_task,
        'resize_image':     tasks.resize_image_task,
        'any_to_pdf':       tasks.any_to_pdf_task,
        'password_protect': tasks.password_protect_task,
        'unlock_pdf':       tasks.unlock_pdf_task,
        'rotate_pdf':       tasks.rotate_pdf_task,
        'watermark_pdf':    tasks.watermark_pdf_task,
        'add_page_numbers': tasks.add_page_numbers_task,
        # Round 2
        'pdf_to_excel':     tasks.pdf_to_excel_task,
        'excel_to_pdf':     tasks.excel_to_pdf_task,
        'pptx_to_pdf':      tasks.pptx_to_pdf_task,
        'pdf_to_pptx':      tasks.pdf_to_pptx_task,
        'html_to_pdf':      tasks.html_to_pdf_task,
        'ocr_pdf':          tasks.ocr_pdf_task,
        'extract_text':     tasks.extract_text_task,
        'extract_images':   tasks.extract_images_task,
        # Round 6
        'edit_metadata':    tasks.edit_metadata_task,
        'flatten_pdf':      tasks.flatten_pdf_task,
        'grayscale_pdf':    tasks.grayscale_pdf_task,
        'crop_pdf':         tasks.crop_pdf_task,
    }
    fn = task_map.get(tool_slug)
    if not fn:
        return
    kwargs = {'job_id': str(job.id)}
    if extra_kwargs:
        kwargs.update(extra_kwargs)
    try:
        fn.apply_async(kwargs=kwargs)
    except Exception as e:
        job.refresh_from_db()
        job.status = 'failed'
        job.error_message = f'Service unavailable: {str(e)}. Please check background worker connection.'
        job.save(update_fields=['status', 'error_message'])


def _track_session(request, job_id):
    ids = request.session.get('dashboard_jobs', [])
    sid = str(job_id)
    if sid not in ids:
        ids.insert(0, sid)
    request.session['dashboard_jobs'] = ids[:50]


def _make_job(request, tool_slug, uploaded_file, extra_save_kwargs=None):
    is_guest = not request.user.is_authenticated
    job = ConversionJob(
        tool=tool_slug,
        input_file=uploaded_file,
        input_size=uploaded_file.size,
        original_name=uploaded_file.name,
        is_guest=is_guest,
        user=request.user if not is_guest else None,
    )
    if extra_save_kwargs:
        for k, v in extra_save_kwargs.items():
            setattr(job, k, v)
    job.save()
    return job


def _render_rotate_thumbnails(job):
    """Render low-res page JPEGs for the rotate live-preview UI."""
    import fitz
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    doc = fitz.open(job.input_file.path)
    mat = fitz.Matrix(96 / 72, 96 / 72)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat, alpha=False)
        path = f"rotate_previews/{job.id}/page_{i}.jpg"
        default_storage.save(path, ContentFile(pix.tobytes("jpeg")))
    page_count = len(doc)
    doc.close()
    return page_count


# ─────────────────────────────────────────────────────────────
#  Public views
# ─────────────────────────────────────────────────────────────

def index(request):
    tools = list(TOOL_CONFIG.items())
    url_hints = [
        {'label': 'PDF link',      'url': 'https://www.w3.org/WAI/WCAG21/wcag-2.1.pdf'},
        {'label': 'Image link',    'url': 'https://www.w3.org/Icons/w3c_home.png'},
        {'label': 'Any web page',  'url': 'https://en.wikipedia.org/wiki/PDF'},
    ]
    
    recent_tools = []
    if request.user.is_authenticated:
        jobs = ConversionJob.objects.filter(user=request.user).order_by('-created_at')
        seen = set()
        for j in jobs:
            if j.tool and j.tool in TOOL_CONFIG and j.tool not in seen:
                recent_tools.append((j.tool, TOOL_CONFIG[j.tool]))
                seen.add(j.tool)
            if len(recent_tools) == 3:
                break
                
    return render(request, 'index.html', {
        'tools': tools, 
        'url_hints': url_hints,
        'recent_tools': recent_tools
    })


def terms_view(request):
    return render(request, 'converter/terms.html')

def pricing_view(request):
    return render(request, 'converter/pricing.html')


def privacy_view(request):
    return render(request, 'pages/privacy.html')


def upload_form(request, tool_slug):
    if tool_slug not in TOOL_CONFIG:
        raise Http404
    config = TOOL_CONFIG[tool_slug]
    return render(request, 'converter/upload.html', {
        'tool_slug': tool_slug,
        'tool': config,
        'form': config['form'](),
    })


@require_http_methods(["POST"])
def upload_file(request, tool_slug):
    if tool_slug not in TOOL_CONFIG:
        raise Http404
    config = TOOL_CONFIG[tool_slug]
    form = config['form'](request.POST, request.FILES)
 
    def _err(msg=None):
        if msg:
            form.add_error('file', msg)
        return render(request, 'converter/upload.html', {
            'tool_slug': tool_slug, 'tool': config,
            'form': form, 'errors': form.errors,
        })
 
    if not form.is_valid():
        return _err()
 
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return _err('No file uploaded.')
 
    valid, error = validate_file(uploaded_file, tool_slug)
    if not valid:
        return _err(error)
 
    extra_kwargs = {}
 
    if tool_slug == 'merge_pdf':
        job = _make_job(request, tool_slug, uploaded_file)
        # Save extra files to disk, collect paths, pass as task kwargs
        # (previously stored in error_message field — that was a bug)
        extra_paths = []
        for f in request.FILES.getlist('file')[1:]:
            extra_job = ConversionJob(tool='merge_pdf', input_file=f,
                                      input_size=f.size, is_guest=True)
            extra_job.save()
            extra_paths.append(extra_job.input_file.path)
            ConversionJob.objects.filter(id=extra_job.id).delete()
        extra_kwargs = {'extra_paths': extra_paths}
 
    elif tool_slug == 'split_pdf':
        job = _make_job(request, tool_slug, uploaded_file)
        extra_kwargs = {
            'start_page': form.cleaned_data.get('start_page'),
            'end_page':   form.cleaned_data.get('end_page'),
        }
 
    elif tool_slug == 'resize_image':
        job = _make_job(request, tool_slug, uploaded_file)
        extra_kwargs = {
            'width':  form.cleaned_data.get('width'),
            'height': form.cleaned_data.get('height'),
        }
 
    elif tool_slug == 'compress_pdf':
        job = _make_job(request, tool_slug, uploaded_file)
        extra_kwargs = {'level': request.POST.get('level', 'recommended')}
 
    elif tool_slug == 'pdf_to_images':
        job = _make_job(request, tool_slug, uploaded_file)
        extra_kwargs = {
            'dpi':        request.POST.get('dpi', '150'),
            'img_format': request.POST.get('img_format', 'png'),
        }
 
    elif tool_slug == 'png_to_jpg':
        job = _make_job(request, tool_slug, uploaded_file)
        try:
            q = max(10, min(95, int(request.POST.get('quality', 85))))
        except (ValueError, TypeError):
            q = 85
        extra_kwargs = {'quality': q}
 
    elif tool_slug == 'password_protect':
        job = _make_job(request, tool_slug, uploaded_file)
        extra_kwargs = {
            'user_password':  form.cleaned_data.get('user_password', ''),
            'owner_password': '',
        }
 
    elif tool_slug == 'unlock_pdf':
        job = _make_job(request, tool_slug, uploaded_file)
        extra_kwargs = {'password': form.cleaned_data.get('password', '')}
 
    elif tool_slug == 'rotate_pdf':
        job = _make_job(request, tool_slug, uploaded_file)
        try:
            page_count = _render_rotate_thumbnails(job)
            job.error_message = f'PAGES:{page_count}'
            job.save(update_fields=['error_message'])
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save(update_fields=['status', 'error_message'])
            return redirect('job_status', uuid=job.id)
        if not request.user.is_authenticated:
            _track_session(request, job.id)
        return redirect('rotate_preview', job_id=job.id)
 
    elif tool_slug == 'watermark_pdf':
        job = _make_job(request, tool_slug, uploaded_file)
        try:
            op = max(5, min(80, int(request.POST.get('opacity', 30))))
        except (ValueError, TypeError):
            op = 30
        extra_kwargs = {
            'watermark_text': request.POST.get('watermark_text', 'CONFIDENTIAL')[:50],
            'opacity':        op,
            'position':       request.POST.get('position', 'diagonal'),
        }
 
    elif tool_slug == 'add_page_numbers':
        job = _make_job(request, tool_slug, uploaded_file)
        try:
            start = max(1, int(request.POST.get('start_number', 1)))
        except (ValueError, TypeError):
            start = 1
        try:
            fsize = max(6, min(24, int(request.POST.get('font_size', 10))))
        except (ValueError, TypeError):
            fsize = 10
        extra_kwargs = {
            'position':     request.POST.get('position', 'bottom-center'),
            'start_number': start,
            'font_size':    fsize,
        }
 
    elif tool_slug == 'edit_metadata':
        job = _make_job(request, tool_slug, uploaded_file)
        extra_kwargs = {
            'title':    form.cleaned_data.get('title', ''),
            'author':   form.cleaned_data.get('author', ''),
            'subject':  form.cleaned_data.get('subject', ''),
            'keywords': form.cleaned_data.get('keywords', ''),
        }
 
    elif tool_slug == 'crop_pdf':
        job = _make_job(request, tool_slug, uploaded_file)
        extra_kwargs = {
            'margin_top':    form.cleaned_data.get('margin_top') or 0,
            'margin_bottom': form.cleaned_data.get('margin_bottom') or 0,
            'margin_left':   form.cleaned_data.get('margin_left') or 0,
            'margin_right':  form.cleaned_data.get('margin_right') or 0,
        }
 

    else:
        job = _make_job(request, tool_slug, uploaded_file)
 
    _dispatch_task(tool_slug, job, extra_kwargs)
 
    if not request.user.is_authenticated:
        _track_session(request, job.id)
 
    return redirect('job_status', uuid=job.id)

@require_http_methods(["POST"])
def universal_upload(request):
    files = request.FILES.getlist('files')
    if not files:
        return redirect('index')
 
    max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024)
    created_ids = []
 
    for f in files:
        if f.size > max_size:
            continue
        job = _make_job(request, 'any_to_pdf', f)
        _dispatch_task('any_to_pdf', job)
        if not request.user.is_authenticated:
            _track_session(request, job.id)
        created_ids.append(str(job.id))
 
    if not created_ids:
        return redirect('index')
 
    # Single file — go to the individual status page as before
    if len(created_ids) == 1:
        return redirect('job_status', uuid=created_ids[0])
 
    # Multiple files — go to the new batch status page
    # Store batch IDs in session so the page can verify ownership
    import uuid as _uuid
    batch_id = _uuid.uuid4().hex
    request.session[f'batch_{batch_id}'] = created_ids
    return redirect('batch_status', batch_id=batch_id)


# ─────────────────────────────────────────────────────────────
#  Rotate PDF — live preview views
# ─────────────────────────────────────────────────────────────

def rotate_preview(request, job_id):
    job = get_object_or_404(ConversionJob, id=job_id)
    page_count = 0
    if job.error_message and job.error_message.startswith('PAGES:'):
        try:
            page_count = int(job.error_message.split(':', 1)[1])
        except ValueError:
            pass
    from django.core.files.storage import default_storage
    thumb_urls = [
        default_storage.url(f"rotate_previews/{job.id}/page_{i}.jpg")
        for i in range(page_count)
    ]
    return render(request, 'converter/rotate_preview.html', {
        'job':        job,
        'job_id':     str(job.id),
        'filename':   job.original_name or job.display_name,
        'page_count': page_count,
        'thumb_urls': thumb_urls,
    })


@require_http_methods(["POST"])
def rotate_apply(request, job_id):
    from .tasks import rotate_pdf_task
    job = get_object_or_404(ConversionJob, id=job_id)
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    rotations = payload.get('rotations', {})
    if not rotations:
        return JsonResponse({'error': 'No rotations provided'}, status=400)
    job.error_message = None
    job.status = 'pending'
    job.save(update_fields=['error_message', 'status'])
    try:
        rotate_pdf_task.apply_async(kwargs={'job_id': str(job.id), 'rotations': rotations})
    except Exception:
        try:
            rotate_pdf_task(job_id=str(job.id), rotations=rotations)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'status': 'pending'})


# ─────────────────────────────────────────────────────────────
#  Dashboard
# ─────────────────────────────────────────────────────────────

PER_PAGE = 25

from api.models import Profile
import uuid as _uuid_lib

def dashboard(request):
    api_profile = None
    if request.user.is_authenticated:
        all_jobs = list(ConversionJob.objects.filter(user=request.user).order_by('-created_at'))
        api_profile, created = Profile.objects.get_or_create(user=request.user)
        
        # Handle API Actions
        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'regen_key':
                api_profile.api_key = _uuid_lib.uuid4()
                api_profile.save()
                messages.success(request, "API Key rotated successfully.")
            elif action == 'save_webhook':
                url = request.POST.get('webhook_url', '').strip()
                api_profile.webhook_url = url if url else None
                api_profile.save()
                messages.success(request, "Webhook URL updated successfully.")
            return redirect('dashboard')
    else:
        ids = request.session.get('dashboard_jobs', [])
        all_jobs = []
        valid_ids = []
        for jid in ids:
            try:
                j = ConversionJob.objects.get(id=jid)
                all_jobs.append(j)
                valid_ids.append(jid)
            except ConversionJob.DoesNotExist:
                pass
        request.session['dashboard_jobs'] = valid_ids

    total_jobs  = len(all_jobs)
    done_jobs   = sum(1 for j in all_jobs if j.status == 'done')
    failed_jobs = sum(1 for j in all_jobs if j.status == 'failed')
    active_jobs = sum(1 for j in all_jobs if j.status in ('pending', 'processing'))
    total_in    = sum(j.input_size for j in all_jobs)
    total_out   = sum(j.output_size for j in all_jobs if j.output_size)

    paginator = Paginator(all_jobs, PER_PAGE)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'dashboard.html', {
        'jobs':        page_obj.object_list,
        'page_obj':    page_obj,
        'total_jobs':  total_jobs,
        'done_jobs':   done_jobs,
        'failed_jobs': failed_jobs,
        'active_jobs': active_jobs,
        'total_in':    human_readable_size(total_in),
        'total_out':   human_readable_size(total_out),
        'total_in_bytes': total_in,
        'total_size':  human_readable_size(total_in),
        'tool_config': TOOL_CONFIG,
        'guest_expiry_min': getattr(settings, 'GUEST_EXPIRY_MINUTES', 5),
        'api_profile': api_profile,
    })


def dashboard_clear(request):
    if request.user.is_authenticated:
        ConversionJob.objects.filter(user=request.user).delete()
    else:
        ids = request.session.get('dashboard_jobs', [])
        ConversionJob.objects.filter(id__in=ids).delete()
        request.session['dashboard_jobs'] = []
    return redirect('dashboard')


def dashboard_delete_job(request, uuid):
    job = get_object_or_404(ConversionJob, id=uuid)
    if request.user.is_authenticated:
        if job.user != request.user:
            raise Http404
    else:
        ids = request.session.get('dashboard_jobs', [])
        if str(uuid) not in ids:
            raise Http404
    for f in [job.input_file, job.output_file]:
        if f:
            try:
                if os.path.exists(f.path):
                    os.remove(f.path)
            except Exception:
                pass
    job.delete()
    if not request.user.is_authenticated:
        ids = request.session.get('dashboard_jobs', [])
        request.session['dashboard_jobs'] = [i for i in ids if i != str(uuid)]
    return redirect('dashboard')


def dashboard_delete_job(request, uuid):
    job = get_object_or_404(ConversionJob, id=uuid)
    if request.user.is_authenticated:
        if job.user != request.user:
            raise Http404
    else:
        ids = request.session.get('dashboard_jobs', [])
        if str(uuid) not in ids:
            raise Http404
    for f in [job.input_file, job.output_file]:
        if f:
            try:
                if os.path.exists(f.path):
                    os.remove(f.path)
            except Exception:
                pass
    job.delete()
    if not request.user.is_authenticated:
        ids = request.session.get('dashboard_jobs', [])
        request.session['dashboard_jobs'] = [i for i in ids if i != str(uuid)]
    return redirect('dashboard')


# ─────────────────────────────────────────────────────────────
#  Job Retry
# ─────────────────────────────────────────────────────────────

@require_http_methods(["POST"])
def job_retry(request, uuid):
    """Re-run a job using the same input file to create a brand-new ConversionJob."""
    original = get_object_or_404(ConversionJob, id=uuid)

    # Ownership check
    if request.user.is_authenticated:
        if original.user and original.user != request.user:
            raise Http404
    else:
        session_ids = request.session.get('dashboard_jobs', [])
        if str(uuid) not in session_ids:
            raise Http404

    if not original.input_file or not os.path.exists(original.input_file.path):
        messages.error(request, 'Original file is no longer available — please re-upload.')
        return redirect('dashboard')

    # Create a new job copying the original input file reference
    from django.core.files import File
    is_guest = not request.user.is_authenticated
    new_job = ConversionJob(
        tool=original.tool,
        input_size=original.input_size,
        original_name=original.original_name,
        is_guest=is_guest,
        user=request.user if not is_guest else None,
    )
    with open(original.input_file.path, 'rb') as fh:
        new_job.input_file.save(
            Path(original.input_file.name).name,
            File(fh),
            save=False,
        )
    new_job.save()

    _dispatch_task(original.tool, new_job)

    if not request.user.is_authenticated:
        _track_session(request, new_job.id)

    return redirect('job_status', uuid=new_job.id)


# ─────────────────────────────────────────────────────────────
#  CSV Export
# ─────────────────────────────────────────────────────────────

@login_required
def export_csv(request):
    """Stream the logged-in user's full conversion history as a CSV."""
    jobs = ConversionJob.objects.filter(user=request.user).order_by('-created_at')

    def rows():
        yield 'File,Tool,Status,Input Size (bytes),Output Size (bytes),Created\r\n'
        for job in jobs:
            yield ','.join([
                f'"{job.display_name}"',
                f'"{job.tool_display}"',
                job.status,
                str(job.input_size),
                str(job.output_size or 0),
                job.created_at.strftime('%Y-%m-%d %H:%M UTC'),
            ]) + '\r\n'

    response = StreamingHttpResponse(rows(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="docshift_history.csv"'
    return response


# ─────────────────────────────────────────────────────────────
#  Account
# ─────────────────────────────────────────────────────────────

@login_required
def account(request):
    profile   = request.user.profile
    jobs      = ConversionJob.objects.filter(user=request.user)
    total_in  = sum(j.input_size  for j in jobs)
    total_out = sum(j.output_size for j in jobs if j.output_size)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_profile':
            bio = request.POST.get('bio', '').strip()[:200]
            profile.bio = bio
            profile.save(update_fields=['bio'])
            messages.success(request, 'Profile updated.')
            return redirect('account')
        elif action == 'delete_account':
            user = request.user
            auth_logout(request)
            user.delete()
            messages.success(request, 'Your account has been deleted.')
            return redirect('index')
    import json as _json
    from django.db.models import Count
    from datetime import date, timedelta

    # Top 5 most-used tools
    top_tools = (
        jobs.values('tool')
            .annotate(count=Count('tool'))
            .order_by('-count')[:5]
    )
    for t in top_tools:
        t['name'] = dict(ConversionJob.TOOL_CHOICES).get(t['tool'], t['tool'])

    # 14-day daily conversion counts
    today = date.today()
    day_labels = [(today - timedelta(days=d)).strftime('%d %b') for d in range(13, -1, -1)]
    day_counts = [0] * 14
    for j in jobs:
        delta = (today - j.created_at.date()).days
        if 0 <= delta < 14:
            day_counts[13 - delta] += 1
    max_count = max(day_counts) or 1

    return render(request, 'account/profile.html', {
        'profile':       profile,
        'jobs':          jobs,
        'total_jobs':    jobs.count(),
        'done_jobs':     jobs.filter(status='done').count(),
        'total_in':      human_readable_size(total_in),
        'total_out':     human_readable_size(total_out),
        'top_tools':     list(top_tools),
        'day_labels':    _json.dumps(day_labels),
        'day_counts':    _json.dumps(day_counts),
        'max_count':     max_count,
    })


# ─────────────────────────────────────────────────────────────
#  Job endpoints
# ─────────────────────────────────────────────────────────────

def job_status(request, uuid):
    job = get_object_or_404(ConversionJob, id=uuid)
    config = TOOL_CONFIG.get(job.tool, {
        'name': job.tool_display, 'icon': '📄',
        'description': '', 'accept': '',
    })
    return render(request, 'converter/status.html', {
        'job': job,
        'tool': config,
        'input_size_human':  human_readable_size(job.input_size),
        'output_size_human': human_readable_size(job.output_size) if job.output_size else None,
        'expiry_seconds':    job.seconds_until_expiry(),
    })


def job_status_json(request, uuid):
    job = get_object_or_404(ConversionJob, id=uuid)
    progress = {'pending': 5, 'processing': 55, 'done': 100, 'failed': 100}.get(job.status, 0)
    return JsonResponse({
        'status':            job.status,
        'progress':          progress,
        'input_size':        job.input_size,
        'output_size':       job.output_size,
        'input_size_human':  human_readable_size(job.input_size),
        'output_size_human': human_readable_size(job.output_size) if job.output_size else None,
        'compression_ratio': job.compression_ratio,
        'tool_name':         job.tool_display,
        'original_name':     job.original_name or job.display_name,
        'error_message':     job.error_message if job.status == 'failed' else None,
        'download_url':      f'/job/{uuid}/download/' if job.status == 'done' and job.output_file else None,
        'expiry_seconds':    job.seconds_until_expiry(),
        'is_guest':          job.is_guest,
    })


"""
SECURITY FIXES FOR converter/views.py
======================================
Three targeted replacements. Do NOT replace the entire file.
Find each function by name and replace just that function.
"""
 
 
# ── FIX 1: job_download — add ownership check ─────────────────────────────
# Find:  def job_download(request, uuid):
# Replace the ENTIRE function with this:
 
def job_download(request, uuid):
    job = get_object_or_404(ConversionJob, id=uuid)
 
    # ── Ownership check ──────────────────────────────────────────────────
    # Logged-in users: job must belong to them
    # Guests: job ID must be in their session
    if request.user.is_authenticated:
        if job.user and job.user != request.user:
            raise Http404("File not found")
    else:
        session_ids = request.session.get('dashboard_jobs', [])
        if str(uuid) not in session_ids and job.user is not None:
            raise Http404("File not found")
    # ────────────────────────────────────────────────────────────────────
 
    if job.status != 'done' or not job.output_file:
        raise Http404("File not ready")
        
    try:
        # Remote Storage (S3 / Cloudflare R2) => Native direct download link
        if hasattr(job.output_file.storage, 'bucket_name'):
            from django.shortcuts import redirect
            filename = Path(job.output_file.name).name
            presigned_url = job.output_file.storage.url(
                job.output_file.name,
                parameters={'ResponseContentDisposition': f'attachment; filename="{filename}"'}
            )
            return redirect(presigned_url)
            
        # Local fallback
        file_path = job.output_file.path
        if not os.path.exists(file_path):
            raise Http404("File not found on disk")
        filename = Path(file_path).name
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Http404("Issue generating download URL")


# ── FIX 2: job_preview — add ownership check ──────────────────────────────
# Find:  def job_preview(request, uuid):
# Replace the ENTIRE function with this:
 
def job_preview(request, uuid):
    job = get_object_or_404(ConversionJob, id=uuid)
 
    # ── Ownership check ──────────────────────────────────────────────────
    if request.user.is_authenticated:
        if job.user and job.user != request.user:
            raise Http404("File not found")
    else:
        session_ids = request.session.get('dashboard_jobs', [])
        if str(uuid) not in session_ids and job.user is not None:
            raise Http404("File not found")
    # ────────────────────────────────────────────────────────────────────
 
    if not job.output_file:
        raise Http404("No output file")
        
    try:
        # Remote Storage (S3 / Cloudflare R2) => Native direct link
        if hasattr(job.output_file.storage, 'bucket_name'):
            from django.shortcuts import redirect
            return redirect(job.output_file.url)
            
        file_path = job.output_file.path
        if not os.path.exists(file_path):
            raise Http404("File not found")
        ext = Path(file_path).suffix.lower()
        mime_map = {
            '.pdf':  'application/pdf',
            '.png':  'image/png',
            '.jpg':  'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.txt':  'text/plain',
            '.zip':  'application/zip',
        }
        content_type = mime_map.get(ext, 'application/octet-stream')
        response = FileResponse(open(file_path, 'rb'), content_type=content_type)
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Content-Disposition'] = f'inline; filename="{Path(file_path).name}"'
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Http404("Issue generating preview URL")

def batch_status(request, batch_id):
    """Live batch status page — shows all jobs from a multi-file upload."""
    job_ids = request.session.get(f'batch_{batch_id}', [])
    if not job_ids:
        # Batch expired or invalid — redirect to dashboard
        return redirect('dashboard')
 
    jobs = []
    for jid in job_ids:
        try:
            jobs.append(ConversionJob.objects.get(id=jid))
        except ConversionJob.DoesNotExist:
            pass
 
    if not jobs:
        return redirect('dashboard')
 
    total     = len(jobs)
    done      = sum(1 for j in jobs if j.status == 'done')
    failed    = sum(1 for j in jobs if j.status == 'failed')
    active    = sum(1 for j in jobs if j.status in ('pending', 'processing'))
    all_done  = (done + failed) == total
 
    return render(request, 'converter/batch.html', {
        'jobs':      jobs,
        'batch_id':  batch_id,
        'total':     total,
        'done':      done,
        'failed':    failed,
        'active':    active,
        'all_done':  all_done,
        'job_ids':   job_ids,
    })
 
 
def batch_status_json(request, batch_id):
    """JSON endpoint polled by the batch page."""
    job_ids = request.session.get(f'batch_{batch_id}', [])
    if not job_ids:
        return JsonResponse({'error': 'Batch not found'}, status=404)
 
    jobs_data = []
    done = failed = 0
 
    for jid in job_ids:
        try:
            job = ConversionJob.objects.get(id=jid)
            progress = {'pending': 5, 'processing': 55,
                        'done': 100, 'failed': 100}.get(job.status, 0)
            jobs_data.append({
                'id':           str(job.id),
                'status':       job.status,
                'progress':     progress,
                'name':         job.display_name,
                'output_ext':   job.output_ext,
                'output_size':  human_readable_size(job.output_size) if job.output_size else None,
                'download_url': f'/job/{job.id}/download/' if job.status == 'done' and job.output_file else None,
                'error':        job.error_message if job.status == 'failed' else None,
            })
            if job.status == 'done':   done += 1
            if job.status == 'failed': failed += 1
        except ConversionJob.DoesNotExist:
            pass
 
    total    = len(job_ids)
    all_done = (done + failed) == total
 
    return JsonResponse({
        'jobs':     jobs_data,
        'total':    total,
        'done':     done,
        'failed':   failed,
        'all_done': all_done,
    })
 
def batch_download_zip(request, batch_id):
    """Download all completed batch job outputs as a single ZIP."""
    import zipfile
    import io
 
    job_ids = request.session.get(f'batch_{batch_id}', [])
    if not job_ids:
        raise Http404("Batch not found")
 
    # Collect all done jobs
    done_jobs = []
    for jid in job_ids:
        try:
            job = ConversionJob.objects.get(id=jid)
            if job.status == 'done' and job.output_file:
                if os.path.exists(job.output_file.path):
                    done_jobs.append(job)
        except ConversionJob.DoesNotExist:
            pass
 
    if not done_jobs:
        raise Http404("No completed files to download")
 
    # Build ZIP in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        seen_names = {}
        for job in done_jobs:
            filename = Path(job.output_file.path).name
            # Deduplicate filenames
            if filename in seen_names:
                seen_names[filename] += 1
                stem = Path(filename).stem
                ext  = Path(filename).suffix
                filename = f"{stem}_{seen_names[filename]}{ext}"
            else:
                seen_names[filename] = 1
            zf.write(job.output_file.path, filename)
 
    buf.seek(0)
    response = FileResponse(buf, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="docshift_batch_{batch_id[:8]}.zip"'
    return response

@require_http_methods(["POST"])
def url_upload(request):
    """Fetch a URL and convert it to PDF."""
    import tempfile
    import requests as req_lib
 
    url = (request.POST.get('url') or '').strip()
    if not url:
        return redirect('index')
 
    # Basic validation
    if not url.startswith(('http://', 'https://')):
        return redirect('index')
 
    MAX_SIZE = getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024)
    TIMEOUT  = 15   # seconds
 
    try:
        # HEAD request first to check content type and size cheaply
        try:
            head = req_lib.head(url, timeout=8, allow_redirects=True,
                                headers={'User-Agent': 'DocShift/1.0'})
            content_type   = head.headers.get('Content-Type', '').lower()
            content_length = int(head.headers.get('Content-Length', 0))
        except Exception:
            content_type   = ''
            content_length = 0
 
        if content_length > MAX_SIZE:
            return redirect('index')
 
        # Fetch the actual content
        resp = req_lib.get(url, timeout=TIMEOUT, stream=True,
                           headers={'User-Agent': 'DocShift/1.0'})
        resp.raise_for_status()
 
        # Read up to MAX_SIZE
        chunks = []
        received = 0
        for chunk in resp.iter_content(chunk_size=65536):
            chunks.append(chunk)
            received += len(chunk)
            if received > MAX_SIZE:
                return redirect('index')
        content = b''.join(chunks)
 
        if not content_type:
            content_type = resp.headers.get('Content-Type', '').lower()
 
        # Determine tool and filename from URL + content type
        from urllib.parse import urlparse
        parsed   = urlparse(url)
        url_path = parsed.path.rstrip('/')
        url_name = Path(url_path).name or 'download'
        url_ext  = Path(url_name).suffix.lower()
 
        # Map content type / extension → tool
        if 'pdf' in content_type or url_ext == '.pdf':
            tool = 'compress_pdf'
            ext  = '.pdf'
            name = url_name if url_ext == '.pdf' else url_name + '.pdf'
        elif any(t in content_type for t in ['jpeg','jpg','png','webp','gif','bmp']) or \
             url_ext in ('.jpg','.jpeg','.png','.webp','.gif','.bmp'):
            tool = 'img_to_pdf'
            ext  = url_ext or '.jpg'
            name = url_name
        elif 'word' in content_type or 'docx' in content_type or url_ext == '.docx':
            tool = 'docx_to_pdf'
            ext  = '.docx'
            name = url_name if url_ext == '.docx' else url_name + '.docx'
        elif 'text/plain' in content_type or url_ext == '.txt':
            tool = 'txt_to_pdf'
            ext  = '.txt'
            name = url_name if url_ext == '.txt' else url_name + '.txt'
        else:
            # Fallback: treat as HTML → PDF
            tool = 'html_to_pdf'
            ext  = '.html'
            name = (url_name if url_ext in ('.html','.htm') else url_name + '.html') or 'page.html'
 
        # Write content to a temp file and create a Django InMemoryUploadedFile
        from django.core.files.uploadedfile import InMemoryUploadedFile
        import io
        file_obj = InMemoryUploadedFile(
            file=io.BytesIO(content),
            field_name='file',
            name=name,
            content_type=content_type or 'application/octet-stream',
            size=len(content),
            charset=None,
        )
 
        # Create the job and dispatch
        is_guest = not request.user.is_authenticated
        job = ConversionJob(
            tool=tool,
            input_file=file_obj,
            input_size=len(content),
            original_name=name,
            is_guest=is_guest,
            user=request.user if not is_guest else None,
        )
        job.save()
 
        _dispatch_task(tool, job)
 
        if is_guest:
            _track_session(request, job.id)
 
        return redirect('job_status', uuid=job.id)
 
    except Exception as e:
        # On any error just go back home — could add a flash message later
        return redirect('index')

# ── API Settings Dashboard ──────────────────────────────────────────
from api.models import Profile
import uuid

@login_required
def dashboard_api(request):
    """
    DEPRECATED: API settings have been merged into the main dashboard tab.
    Redirecting to the unified dashboard.
    """
    return redirect('dashboard')

from .models import SalesInquiry

def contact_sales(request):
    """
    Handles the 'Contact Sales' form for Corporate inquiries.
    Saves leads to the SalesInquiry model.
    """
    if request.method == 'POST':
        name    = request.POST.get('name', '').strip()
        email   = request.POST.get('email', '').strip()
        company = request.POST.get('company', '').strip()
        message = request.POST.get('message', '').strip()
        
        if name and email and message:
            SalesInquiry.objects.create(
                name=name, email=email, company=company, message=message
            )
            messages.success(request, "Your inquiry has been received! Our sales team will reach out shortly.")
            return redirect('/pricing/?contact=success')
        else:
            messages.error(request, "Please fill in all required fields.")
            
    return render(request, 'converter/contact.html')