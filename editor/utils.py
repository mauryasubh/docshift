"""
editor/utils.py — PDF analysis helpers
"""
from pathlib import Path
import pytesseract

MIN_CHARS_FOR_TEXT_PAGE = 20

from django.conf import settings as django_settings
if hasattr(django_settings, 'TESSERACT_CMD'):
    pytesseract.pytesseract.tesseract_cmd = django_settings.TESSERACT_CMD


def detect_pdf_type(doc):
    pages_with_text = 0
    pages_without_text = 0
    for page in doc:
        text = page.get_text("text").strip()
        if len(text) >= MIN_CHARS_FOR_TEXT_PAGE:
            pages_with_text += 1
        else:
            pages_without_text += 1
    total = len(doc)
    if total == 0:
        return 'scanned'
    ratio = pages_with_text / total
    if ratio >= 0.8:   return 'generated'
    elif ratio <= 0.2: return 'scanned'
    else:              return 'mixed'


def extract_text_blocks(doc):
    blocks = []
    block_index = 0
    for page_num, page in enumerate(doc):
        page_dict = page.get_text("dict", flags=0)
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    raw_text = span.get("text", "").strip()
                    if not raw_text:
                        continue
                    bbox = span.get("bbox", [0, 0, 0, 0])
                    x, y, x2, y2 = bbox
                    w, h = x2 - x, y2 - y
                    if w <= 0 or h <= 0:
                        continue
                    font_name = span.get("font", "")
                    font_size = round(span.get("size", 12.0), 2)
                    flags     = span.get("flags", 0)
                    is_bold   = bool(flags & 16)
                    is_italic = bool(flags & 2)
                    raw_color = span.get("color", 0)
                    if isinstance(raw_color, int):
                        r = (raw_color >> 16) & 0xFF
                        g = (raw_color >> 8)  & 0xFF
                        b =  raw_color        & 0xFF
                    else:
                        r, g, b = 0, 0, 0
                    blocks.append({
                        "page": page_num, "block_index": block_index,
                        "x": round(x,2), "y": round(y,2),
                        "w": round(w,2), "h": round(h,2),
                        "text": raw_text,
                        "font_size": font_size, "font_name": font_name,
                        "is_bold": is_bold, "is_italic": is_italic,
                        "color": [r, g, b],
                    })
                    block_index += 1
    return blocks


def extract_images(doc):
    images = []
    image_index = 0
    for page_num, page in enumerate(doc):
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            for rect in page.get_image_rects(xref):
                x, y, x2, y2 = rect.x0, rect.y0, rect.x1, rect.y1
                w, h = x2 - x, y2 - y
                if w <= 1 or h <= 1:
                    continue
                images.append({
                    "page": page_num, "image_index": image_index,
                    "x": round(x,2), "y": round(y,2),
                    "w": round(w,2), "h": round(h,2),
                    "xref": xref,
                })
                image_index += 1
    return images


def render_page_images(doc, output_dir, dpi=150):
    import fitz
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pix.save(str(output_dir / f"page_{i + 1}.png"))
    return len(doc)


def run_ocr_on_page(page, dpi=150):
    try:
        import pytesseract
        from PIL import Image
        import fitz, io
    except ImportError as e:
        raise ImportError(f"OCR requires pytesseract and Pillow: {e}")

    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    scale = 72.0 / dpi

    try:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config="--psm 6")
    except Exception:
        return []

    blocks = []
    block_index = 0
    for i in range(len(data["text"])):
        word = (data["text"][i] or "").strip()
        conf = int(data["conf"][i])
        if not word or conf < 30:
            continue
        x = round(data["left"][i]  * scale, 2)
        y = round(data["top"][i]   * scale, 2)
        w = round(data["width"][i] * scale, 2)
        h = round(data["height"][i]* scale, 2)
        if w <= 0 or h <= 0:
            continue
        blocks.append({
            "page": page.number, "block_index": block_index,
            "x": x, "y": y, "w": w, "h": h,
            "text": word,
            "font_size": round(max(h * 0.72, 6.0), 1),
            "font_name": "Unknown",
            "is_bold": False, "is_italic": False,
            "color": [0, 0, 0],
            "ocr": True, "confidence": conf,
        })
        block_index += 1
    return blocks


def page_dimensions(doc):
    return [{"width": round(p.rect.width, 2), "height": round(p.rect.height, 2)} for p in doc]
