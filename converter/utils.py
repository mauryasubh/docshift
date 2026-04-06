import os, uuid, zipfile, filetype
from pathlib import Path
from django.conf import settings

IMAGE_EXTS  = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif']
IMAGE_MIMES = ['image/jpeg', 'image/jpg', 'image/png', 'image/bmp',
               'image/tiff', 'image/webp', 'image/gif']

PDF_EXTS  = ['.pdf']
PDF_MIMES = ['application/pdf']

XLSX_MIMES = [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'application/zip', 'application/x-zip-compressed',  # xlsx is a zip
]
PPTX_MIMES = [
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.ms-powerpoint',
    'application/zip', 'application/x-zip-compressed',
]
HTML_MIMES = ['text/html', 'text/plain', 'application/xhtml+xml']

ALLOWED_EXTENSIONS = {
    # ── Round 1 ──────────────────────────────────────────────
    'merge_pdf':        PDF_EXTS,
    'compress_pdf':     PDF_EXTS,
    'split_pdf':        PDF_EXTS,
    'pdf_to_images':    PDF_EXTS,
    'pdf_to_word':      PDF_EXTS,
    'docx_to_pdf':      ['.docx'],
    'txt_to_pdf':       ['.txt'],
    'img_to_pdf':       IMAGE_EXTS,
    'jpg_to_png':       ['.jpg', '.jpeg'],
    'png_to_jpg':       ['.png'],
    'resize_image':     IMAGE_EXTS,
    'any_to_pdf':       PDF_EXTS + ['.docx', '.txt'] + IMAGE_EXTS,
    'password_protect': PDF_EXTS,
    'unlock_pdf':       PDF_EXTS,
    'rotate_pdf':       PDF_EXTS,
    'watermark_pdf':    PDF_EXTS,
    'add_page_numbers': PDF_EXTS,
    # ── Round 2 ──────────────────────────────────────────────
    'pdf_to_excel':     PDF_EXTS,
    'excel_to_pdf':     ['.xlsx', '.xls'],
    'pptx_to_pdf':      ['.pptx', '.ppt'],
    'pdf_to_pptx':      PDF_EXTS,
    'html_to_pdf':      ['.html', '.htm'],
    'ocr_pdf':          PDF_EXTS,
    'extract_text':     PDF_EXTS,
    'extract_images':   PDF_EXTS,
    # ── Round 6 ──────────────────────────────────────────────
    'edit_metadata':    PDF_EXTS,
    'flatten_pdf':      PDF_EXTS,
    'grayscale_pdf':    PDF_EXTS,
    'crop_pdf':         PDF_EXTS,
}

ALLOWED_MIMES = {
    # ── Round 1 ──────────────────────────────────────────────
    'merge_pdf':        PDF_MIMES,
    'compress_pdf':     PDF_MIMES,
    'split_pdf':        PDF_MIMES,
    'pdf_to_images':    PDF_MIMES,
    'pdf_to_word':      PDF_MIMES,
    'docx_to_pdf':      [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/zip', 'application/x-zip-compressed',
    ],
    'txt_to_pdf':       ['text/plain'],
    'img_to_pdf':       IMAGE_MIMES,
    'jpg_to_png':       ['image/jpeg', 'image/jpg'],
    'png_to_jpg':       ['image/png'],
    'resize_image':     IMAGE_MIMES,
    'any_to_pdf':       PDF_MIMES + [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/zip', 'text/plain',
    ] + IMAGE_MIMES,
    'password_protect': PDF_MIMES,
    'unlock_pdf':       PDF_MIMES,
    'rotate_pdf':       PDF_MIMES,
    'watermark_pdf':    PDF_MIMES,
    'add_page_numbers': PDF_MIMES,
    # ── Round 2 ──────────────────────────────────────────────
    'pdf_to_excel':     PDF_MIMES,
    'excel_to_pdf':     XLSX_MIMES,
    'pptx_to_pdf':      PPTX_MIMES,
    'pdf_to_pptx':      PDF_MIMES,
    'html_to_pdf':      HTML_MIMES,
    'ocr_pdf':          PDF_MIMES,
    'extract_text':     PDF_MIMES,
    'extract_images':   PDF_MIMES,
    # ── Round 6 ──────────────────────────────────────────────
    'edit_metadata':    PDF_MIMES,
    'flatten_pdf':      PDF_MIMES,
    'grayscale_pdf':    PDF_MIMES,
    'crop_pdf':         PDF_MIMES,
}


def validate_file(file, tool):
    ext = Path(file.name).suffix.lower()
    allowed_exts = ALLOWED_EXTENSIONS.get(tool, [])
    if allowed_exts and ext not in allowed_exts:
        return False, f"Invalid file type. Allowed: {', '.join(allowed_exts)}"

    file.seek(0); chunk = file.read(4096); file.seek(0)

    # Plain text files — filetype can't detect them, skip mime check
    if ext in ('.txt', '.html', '.htm'):
        return True, None

    kind = filetype.guess(chunk)
    if kind is None:
        if ext in ['.docx', '.xlsx', '.xls', '.pptx', '.ppt'] + IMAGE_EXTS:
            return True, None
        return False, "Could not detect file type."

    allowed_mimes = ALLOWED_MIMES.get(tool, [])
    if allowed_mimes and kind.mime not in allowed_mimes:
        return False, f"File content doesn't match expected type (detected: {kind.mime})"
    return True, None


def get_output_path(original_name, extension):
    out = Path(settings.MEDIA_ROOT) / 'outputs'
    out.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4()}{extension}"
    return str(out / name), f"outputs/{name}"


def human_readable_size(size_bytes):
    if not size_bytes: return "0 B"
    units, i, s = ['B', 'KB', 'MB', 'GB'], 0, float(size_bytes)
    while s >= 1024 and i < 3: s /= 1024; i += 1
    return f"{s:.1f} {units[i]}"


def create_zip(files_dict, zip_name):
    out = Path(settings.MEDIA_ROOT) / 'outputs'
    out.mkdir(parents=True, exist_ok=True)
    zname = f"{uuid.uuid4()}_{zip_name}"
    zpath = str(out / zname)
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for arcname, fp in files_dict.items():
            zf.write(fp, arcname)
    return zpath, f"outputs/{zname}"


def ext_to_tool(filename):
    ext = Path(filename).suffix.lower()
    if ext == '.pdf':             return 'compress_pdf'
    if ext in ('.docx', '.doc'): return 'docx_to_pdf'
    if ext == '.txt':             return 'txt_to_pdf'
    if ext in IMAGE_EXTS:         return 'img_to_pdf'
    return 'any_to_pdf'