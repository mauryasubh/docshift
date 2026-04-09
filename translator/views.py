import os
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .models import TranslationJob
from .tasks import translate_docx_task

MAX_SIZE = getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024)

LANG_CHOICES = [
    ('auto', 'Auto-detect'),
    ('en',   'English'),
    ('fr',   'French'),
    ('es',   'Spanish'),
    ('de',   'German'),
    ('it',   'Italian'),
    ('pt',   'Portuguese'),
]


def translator_home(request):
    return render(request, 'translator/upload.html', {'lang_choices': LANG_CHOICES})


@require_http_methods(["POST"])
def translator_upload(request):

    def _err(msg):
        return render(request, 'translator/upload.html', {
            'lang_choices': LANG_CHOICES, 'error': msg,
        })

    uploaded = request.FILES.get('file')
    if not uploaded:
        return _err('No file uploaded.')

    ext = Path(uploaded.name).suffix.lower()
    if ext not in ('.docx', '.pdf'):
        return _err('Only .docx and .pdf files are supported.')

    if uploaded.size > MAX_SIZE:
        return _err(f'File too large. Max {MAX_SIZE // (1024*1024)} MB.')

    source_lang = request.POST.get('source_lang', 'auto')
    target_lang = request.POST.get('target_lang', 'en')

    if source_lang == target_lang and source_lang != 'auto':
        return _err('Source and target language cannot be the same.')

    from .utils import check_language_pair
    ok, msg = check_language_pair(source_lang, target_lang)
    if not ok:
        return _err(msg)

    is_guest = not request.user.is_authenticated
    job = TranslationJob(
        user          = request.user if not is_guest else None,
        is_guest      = is_guest,
        original_file = uploaded,
        original_name = uploaded.name,
        original_size = uploaded.size,
        source_lang   = source_lang,
        target_lang   = target_lang,
    )
    job.save()

    if is_guest:
        ids = request.session.get('translation_jobs', [])
        ids.insert(0, str(job.id))
        request.session['translation_jobs'] = ids[:20]

    try:
        if ext == '.docx':
            translate_docx_task.apply_async(args=[str(job.id)])
        else:
            from .tasks import translate_pdf_task
            translate_pdf_task.apply_async(args=[str(job.id)])
    except Exception:
        try:
            if ext == '.docx':
                translate_docx_task(str(job.id))
            else:
                from .tasks import translate_pdf_task
                translate_pdf_task(str(job.id))
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save(update_fields=['status', 'error_message'])

    return redirect('translator_result', job_id=job.id)


def translator_result(request, job_id):
    job = get_object_or_404(TranslationJob, id=job_id)
    return render(request, 'translator/result.html', {
        'job': job, 'expiry_seconds': job.seconds_until_expiry(),
    })


def translator_status_json(request, job_id):
    job = get_object_or_404(TranslationJob, id=job_id)
    progress = {'pending': 10, 'processing': 55, 'done': 100, 'failed': 100}.get(job.status, 0)
    return JsonResponse({
        'status':         job.status,
        'progress':       progress,
        'char_count':     job.char_count,
        'result_size':    job.result_size,
        'error_message':  job.error_message if job.status == 'failed' else None,
        'download_url':   f'/translator/job/{job_id}/download/'
                          if job.status == 'done' and job.result_file else None,
        'expiry_seconds': job.seconds_until_expiry(),
    })


def translator_download(request, job_id):
    job = get_object_or_404(TranslationJob, id=job_id)
    if job.status != 'done' or not job.result_file:
        raise Http404("File not ready.")
        
    try:
        # Remote Storage (S3 / Cloudflare R2) => Native direct download link
        if hasattr(job.result_file.storage, 'bucket_name'):
            from django.shortcuts import redirect
            return redirect(job.result_file.url)
            
        # Local fallback
        path = job.result_file.path
        if not os.path.exists(path):
            raise Http404("File not found on disk.")
        return FileResponse(open(path, 'rb'), as_attachment=True, filename=Path(path).name)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Http404("Issue generating download URL")
