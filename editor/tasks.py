"""
editor/tasks.py — v4: fix overflow by expanding rect height to fit font
"""
import os, base64, tempfile
from collections import defaultdict
from celery import shared_task
from django.utils import timezone


@shared_task(bind=True)
def analyse_pdf_task(self, session_id):
    from editor.models import EditorSession
    from editor.utils import (detect_pdf_type, extract_text_blocks, extract_images,
                               render_page_images, run_ocr_on_page, page_dimensions,
                               MIN_CHARS_FOR_TEXT_PAGE)
    session = EditorSession.objects.get(id=session_id)
    try:
        import fitz
        session.status = 'analysing'
        session.save(update_fields=['status'])
        doc      = fitz.open(session.original_file.path)
        pdf_type = detect_pdf_type(doc)
        session.pdf_type   = pdf_type
        session.page_count = len(doc)
        session.save(update_fields=['pdf_type', 'page_count'])
        all_blocks = []
        if pdf_type in ('generated', 'mixed'):
            all_blocks.extend(extract_text_blocks(doc))
        if pdf_type in ('scanned', 'mixed'):
            pages_with_text = set()
            if pdf_type == 'mixed':
                for page in doc:
                    if len(page.get_text("text").strip()) >= MIN_CHARS_FOR_TEXT_PAGE:
                        pages_with_text.add(page.number)
            for page in doc:
                if page.number not in pages_with_text:
                    try:
                        all_blocks.extend(run_ocr_on_page(page, dpi=150))
                    except Exception as e:
                        session.error_message = (session.error_message or '') + f"\nOCR p{page.number+1}: {e}"
        images = extract_images(doc)
        render_page_images(doc, str(session.id), dpi=150)
        dims   = page_dimensions(doc)
        doc.close()
        session.blocks_json = [{"type": "meta", "page_dimensions": dims}] + all_blocks
        session.images_json = images
        session.status      = 'ready'
        session.save(update_fields=['blocks_json', 'images_json', 'status', 'error_message'])
    except Exception as e:
        session.status = 'failed'
        session.error_message = str(e)
        session.save(update_fields=['status', 'error_message'])
        raise


@shared_task(bind=True)
def save_edits_task(self, session_id, edits_payload):
    from editor.models import EditorSession
    from django.core.files.base import ContentFile
    import uuid as _uuid

    session = EditorSession.objects.get(id=session_id)
    try:
        import fitz

        session.status = 'saving'
        session.save(update_fields=['status'])

        text_edits    = edits_payload.get('text_edits', [])
        image_actions = edits_payload.get('image_actions', [])
        annotations   = edits_payload.get('annotations', [])

        doc = fitz.open(session.original_file.path)

        # ── Text edits ────────────────────────────────────────
        # Group by page so apply_redactions() runs once per page
        edits_by_page = defaultdict(list)
        for edit in text_edits:
            pg = int(edit.get('page') or 0)
            edits_by_page[pg].append(edit)

        for page_num, page_edits in edits_by_page.items():
            if page_num >= len(doc):
                continue
            page      = doc[page_num]
            page_rect = page.rect   # full page dimensions in PDF pts

            # Pass 1 — redact original text areas
            for edit in page_edits:
                x = _f(edit.get('x'), 0)
                y = _f(edit.get('y'), 0)
                w = _f(edit.get('w'), 50)
                h = _f(edit.get('h'), 12)
                # Expand redact rect slightly to fully cover original text
                redact_rect = fitz.Rect(
                    max(0, x - 1),
                    max(0, y - 1),
                    min(page_rect.width,  x + w + 1),
                    min(page_rect.height, y + h + 1),
                )
                page.add_redact_annot(redact_rect, fill=(1, 1, 1))

            page.apply_redactions()

            # Pass 2 — insert replacement text
            for edit in page_edits:
                new_text = str(edit.get('new_text') or '').strip()
                if not new_text:
                    continue  # deletion — redaction cleared it, done

                x         = _f(edit.get('x'), 0)
                y         = _f(edit.get('y'), 0)
                w         = _f(edit.get('w'), 50)
                orig_h    = _f(edit.get('h'), 12)
                font_size = max(6.0, _f(edit.get('font_size'), 12.0))
                font_name = _safe_font(str(edit.get('font_name') or ''))
                color_f   = _to_color_float(edit.get('color', [0, 0, 0]))

                # ── Key fix: make the insertion rect tall enough ──────
                # PyMuPDF needs at least (font_size * 1.2) height per line.
                # Estimate lines needed, then give enough room down the page.
                line_height   = font_size * 1.5
                chars_per_line = max(1, int(w / (font_size * 0.55)))
                num_lines      = max(1, -(-len(new_text) // chars_per_line))  # ceiling div
                needed_h       = num_lines * line_height + 4

                # Use the larger of original height vs needed height,
                # but never exceed the bottom of the page
                insert_h = max(orig_h, needed_h)
                insert_rect = fitz.Rect(
                    x,
                    y,
                    min(page_rect.width,  x + w),
                    min(page_rect.height, y + insert_h),
                )

                # Try inserting — if still overflows, reduce font size to fit
                rc = page.insert_textbox(
                    insert_rect,
                    new_text,
                    fontsize=font_size,
                    fontname=font_name,
                    color=color_f,
                    align=0,
                )

                # rc < 0 means overflow — shrink font and retry once
                if rc < 0:
                    # Give it the full remaining page height
                    full_rect = fitz.Rect(x, y, min(page_rect.width, x + w), page_rect.height - 10)
                    # Try with smaller font
                    small_size = max(6.0, font_size * 0.75)
                    rc2 = page.insert_textbox(
                        full_rect,
                        new_text,
                        fontsize=small_size,
                        fontname=font_name,
                        color=color_f,
                        align=0,
                    )
                    print(f"[editor save] retry with smaller font {small_size:.1f}pt rc={rc2}")

        # ── Image actions ─────────────────────────────────────
        for act in image_actions:
            page_num = int(act.get('page') or 0)
            if page_num >= len(doc): continue
            page = doc[page_num]
            x = _f(act.get('x'), 0); y = _f(act.get('y'), 0)
            w = _f(act.get('w'), 50); h = _f(act.get('h'), 50)
            rect = fitz.Rect(x, y, x + w, y + h)
            page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()
            if act.get('action') == 'replace':
                b64 = str(act.get('new_image_b64') or '')
                if ',' in b64: b64 = b64.split(',', 1)[1]
                if b64:
                    img_bytes = base64.b64decode(b64)
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        tmp.write(img_bytes); tmp_path = tmp.name
                    try:    page.insert_image(rect, filename=tmp_path)
                    finally:
                        try: os.remove(tmp_path)
                        except: pass

        # ── Annotations ───────────────────────────────────────
        for ann in annotations:
            page_num = int(ann.get('page') or 0)
            if page_num >= len(doc): continue
            page    = doc[page_num]
            x = _f(ann.get('x'), 0); y = _f(ann.get('y'), 0)
            w = _f(ann.get('w'), 50); h = _f(ann.get('h'), 14)
            rect    = fitz.Rect(x, y, x + w, y + h)
            color_f = _to_color_float(ann.get('color', [255, 235, 59]))
            if ann.get('type') == 'highlight':
                shape = page.new_shape()
                shape.draw_rect(rect)
                shape.finish(color=None, fill=color_f, fill_opacity=0.35)
                shape.commit()
            elif ann.get('type') == 'textbox':
                content = str(ann.get('content') or '').strip()
                if content:
                    try:
                        page.insert_textbox(rect, content,
                            fontsize=max(6.0, _f(ann.get('font_size'), 11.0)),
                            fontname='helv', color=color_f, align=0)
                    except Exception as e:
                        print(f"[editor save] ann FAILED: {e}")

        # ── Write output ──────────────────────────────────────
        out_bytes = doc.tobytes(garbage=4, deflate=True, clean=True)
        doc.close()

        result_name = f"edited_{_uuid.uuid4().hex[:8]}_{session.original_name}"
        session.result_file.save(result_name, ContentFile(out_bytes), save=False)
        session.result_size = len(out_bytes)
        session.status      = 'saved'
        session.save(update_fields=['result_file', 'result_size', 'status'])

    except Exception as e:
        import traceback; traceback.print_exc()
        session.status = 'failed'
        session.error_message = str(e)
        session.save(update_fields=['status', 'error_message'])
        raise


@shared_task
def cleanup_editor_sessions():
    from editor.models import EditorSession
    import shutil
    expired = EditorSession.objects.filter(expires_at__lt=timezone.now())
    count = 0
    for session in expired:
        try:
            if session.pages_dir.exists():
                shutil.rmtree(str(session.pages_dir))
        except: pass
        for f in [session.original_file, session.result_file]:
            if f:
                try:
                    if os.path.exists(f.path): os.remove(f.path)
                except: pass
        session.delete()
        count += 1
    return f"Cleaned {count} expired editor sessions"


# ── Helpers ───────────────────────────────────────────────────

def _f(val, default=0.0):
    try:
        return float(val) if val is not None else float(default)
    except (TypeError, ValueError):
        return float(default)


def _to_color_float(raw):
    try:
        if isinstance(raw, (list, tuple)) and len(raw) >= 3:
            r, g, b = float(raw[0] or 0), float(raw[1] or 0), float(raw[2] or 0)
            return (r/255.0, g/255.0, b/255.0) if max(r,g,b) > 1 else (r, g, b)
        if isinstance(raw, int):
            return ((raw>>16&0xFF)/255.0, (raw>>8&0xFF)/255.0, (raw&0xFF)/255.0)
    except Exception:
        pass
    return (0.0, 0.0, 0.0)


def _safe_font(name):
    n = (name or '').lower()
    if any(k in n for k in ('helvetica','arial','sans')):
        if 'bold' in n and ('oblique' in n or 'italic' in n): return 'hebo'
        if 'oblique' in n or 'italic' in n: return 'heoi'
        return 'helv'
    if any(k in n for k in ('times','roman','serif')):
        if 'bold' in n and 'italic' in n: return 'tibi'
        if 'bold' in n:   return 'tibo'
        if 'italic' in n: return 'tiit'
        return 'tiro'
    if any(k in n for k in ('courier','mono','code')):
        if 'bold' in n and ('oblique' in n or 'italic' in n): return 'cobo'
        if 'oblique' in n or 'italic' in n: return 'coit'
        return 'cour'
    return 'helv'
