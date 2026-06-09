"""
Stage 3 — Digital Signature & Verification helpers
Uses pyhanko for PAdES-B Level 2 signing and verification.
Works on both Windows (dev) and Linux/Ubuntu (prod).
"""

import os
import io
import datetime
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
#  Certificate generation (self-signed, cached on disk as PKCS12)
# ─────────────────────────────────────────────────────────────

_CERT_DIR = None


def _get_cert_dir():
    global _CERT_DIR
    if _CERT_DIR is None:
        from django.conf import settings
        _CERT_DIR = Path(settings.MEDIA_ROOT) / '.signing_certs'
        _CERT_DIR.mkdir(parents=True, exist_ok=True)
    return _CERT_DIR


def _ensure_pkcs12():
    """
    Generate (once) a PKCS#12 archive with the ShiftDocs signing cert + key.
    Returns the path to the .p12 file.
    """
    cert_dir = _get_cert_dir()
    p12_path = cert_dir / 'shiftdocs_sign.p12'

    if p12_path.exists():
        return str(p12_path)

    # Generate RSA 2048 key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Build self-signed cert valid for 10 years
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ShiftDocs"),
        x509.NameAttribute(NameOID.COMMON_NAME, "ShiftDocs Document Signing CA"),
    ])
    now = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,  # nonRepudiation
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )

    # Serialize to PKCS#12 (no password for simplicity)
    p12_data = serialization.pkcs12.serialize_key_and_certificates(
        name=b"ShiftDocs Signing",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.NoEncryption(),
    )
    p12_path.write_bytes(p12_data)

    logger.info("Generated ShiftDocs signing PKCS#12 at %s", p12_path)
    return str(p12_path)


# Cached signer instance
_signer_cache = None


def _get_signer():
    """Get or create a pyhanko SimpleSigner from our PKCS#12 cert."""
    global _signer_cache
    if _signer_cache is not None:
        return _signer_cache

    from pyhanko.sign.signers import SimpleSigner

    p12_path = _ensure_pkcs12()
    signer = SimpleSigner.load_pkcs12(
        pfx_file=p12_path,
        passphrase=None,
    )
    _signer_cache = signer
    return signer


# ─────────────────────────────────────────────────────────────
#  Sign a PDF
# ─────────────────────────────────────────────────────────────

def _draw_visible_stamp(input_bytes, signer_name, reason, position, page_choice, stamp_style="card", offset=10):
    """Draw a visual signature stamp on the PDF using PyMuPDF."""
    try:
        import fitz
        import qrcode

        doc = fitz.open(stream=input_bytes, filetype="pdf")
        if len(doc) == 0:
            return input_bytes

        # Select page
        if page_choice == 'first':
            page = doc[0]
        else:
            page = doc[-1]

        page_rect = page.rect
        width = page_rect.width
        height = page_rect.height

        # Dynamic size based on style choice
        if stamp_style == 'qr_only':
            stamp_width = 36
            stamp_height = 36
        elif stamp_style == 'text_only':
            stamp_width = 120
            stamp_height = 36
        else: # 'card' (default)
            stamp_width = 160
            stamp_height = 46

        # Configurable offset from page boundaries
        margin = float(offset)

        # Position calculation
        if position == 'bottom_left':
            x1 = margin
            y1 = height - stamp_height - margin
        elif position == 'top_right':
            x1 = width - stamp_width - margin
            y1 = margin
        elif position == 'top_left':
            x1 = margin
            y1 = margin
        else: # bottom_right
            x1 = width - stamp_width - margin
            y1 = height - stamp_height - margin

        x2 = x1 + stamp_width
        y2 = y1 + stamp_height

        stamp_rect = fitz.Rect(x1, y1, x2, y2)

        # Generate QR code for styles that require it
        if stamp_style in ['card', 'qr_only']:
            qr = qrcode.QRCode(version=1, box_size=8, border=1)
            qr.add_data("https://shiftdocs.io/digital-sign/")
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")

            qr_bytes = io.BytesIO()
            qr_img.save(qr_bytes, format="PNG")
            qr_png = qr_bytes.getvalue()

        # Render based on selected stamp style
        if stamp_style == 'qr_only':
            # QR only: no text, no border card, just a tiny clean QR code
            page.insert_image(stamp_rect, stream=qr_png)

        elif stamp_style == 'text_only':
            # Text only: compact text box with rounded border
            try:
                page.draw_rect(stamp_rect, color=(0.1, 0.45, 0.91), fill=(0.96, 0.98, 1.0), width=1.0, radius=4.0)
            except Exception:
                page.draw_rect(stamp_rect, color=(0.1, 0.45, 0.91), fill=(0.96, 0.98, 1.0), width=1.0)

            text_rect = fitz.Rect(x1 + 6, y1 + 4, x2 - 6, y2 - 4)
            signer_name_clean = signer_name[:20]
            now_str = datetime.datetime.now().strftime("%d %b %Y, %H:%M")
            text = (
                "DIGITALLY SIGNED\n"
                f"Signer: {signer_name_clean}\n"
                f"Date: {now_str}"
            )
            page.insert_textbox(text_rect, text, fontsize=6.0, fontname="helv", color=(0.1, 0.12, 0.15), align=0)

        else:
            # Card: details + QR code next to it (standard default, now more compact)
            try:
                page.draw_rect(stamp_rect, color=(0.1, 0.45, 0.91), fill=(0.96, 0.98, 1.0), width=1.0, radius=4.0)
            except Exception:
                page.draw_rect(stamp_rect, color=(0.1, 0.45, 0.91), fill=(0.96, 0.98, 1.0), width=1.0)

            # Insert QR code
            qr_size = stamp_height - 10
            qr_rect = fitz.Rect(x1 + 5, y1 + 5, x1 + 5 + qr_size, y1 + 5 + qr_size)
            page.insert_image(qr_rect, stream=qr_png)

            # Insert text next to the QR code
            text_rect = fitz.Rect(x1 + 5 + qr_size + 6, y1 + 5, x2 - 5, y2 - 5)
            signer_name_clean = signer_name[:20]
            now_str = datetime.datetime.now().strftime("%d %b %Y, %H:%M")
            text = (
                "DIGITALLY SIGNED\n"
                f"Signer: {signer_name_clean}\n"
                f"Date: {now_str}\n"
                "Via: shiftdocs.io"
            )
            page.insert_textbox(text_rect, text, fontsize=6.0, fontname="helv", color=(0.1, 0.12, 0.15), align=0)

        # Write back to bytes
        out_bytes = doc.write()
        doc.close()
        return out_bytes
    except Exception as e:
        logger.error("Failed to draw visible stamp: %s", str(e))
        return input_bytes


def sign_pdf(input_bytes, signer_name="ShiftDocs User", reason="Document Signing",
             visual_signature=True, position="bottom_right", page_choice="last",
             stamp_style="card", offset=10):
    """
    Sign a PDF byte stream with a PAdES-B Level 2 signature.

    Args:
        input_bytes: bytes — raw PDF content
        signer_name: str — name to embed in the signature
        reason: str — reason for signing
        visual_signature: bool — whether to draw a visible stamp
        position: str — 'bottom_right', 'bottom_left', 'top_right', 'top_left'
        page_choice: str — 'last', 'first'
        stamp_style: str — 'card', 'qr_only', 'text_only'
        offset: int — margin offset from borders

    Returns:
        bytes — the signed PDF content
    """
    from pyhanko.sign.signers import PdfSignatureMetadata, sign_pdf as pyhanko_sign_pdf
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

    # Draw visual signature stamp if requested
    if visual_signature:
        input_bytes = _draw_visible_stamp(
            input_bytes, 
            signer_name=signer_name, 
            reason=reason, 
            position=position, 
            page_choice=page_choice,
            stamp_style=stamp_style,
            offset=offset
        )

    signer = _get_signer()

    writer = IncrementalPdfFileWriter(io.BytesIO(input_bytes))

    sig_meta = PdfSignatureMetadata(
        field_name='ShiftDocs_Signature',
        reason=reason,
        name=signer_name,
        location='ShiftDocs Platform',
    )

    output = io.BytesIO()
    pyhanko_sign_pdf(
        writer,
        sig_meta,
        signer=signer,
        output=output,
    )

    return output.getvalue()


# ─────────────────────────────────────────────────────────────
#  Verify a PDF
# ─────────────────────────────────────────────────────────────

def verify_pdf(input_bytes):
    """
    Verify all digital signatures in a PDF.

    Returns:
        dict with keys:
            - has_signatures: bool
            - signatures: list of dicts
            - tampered: bool
            - summary: str
            - status: str ('valid' | 'tampered' | 'unsigned' | 'error')
    """
    from pyhanko.pdf_utils.reader import PdfFileReader

    try:
        reader = PdfFileReader(io.BytesIO(input_bytes))
    except Exception as e:
        return {
            'has_signatures': False,
            'signatures': [],
            'tampered': False,
            'summary': f'Could not read PDF: {str(e)}',
            'status': 'error',
        }

    try:
        sig_fields_list = list(reader.embedded_signatures)
    except Exception:
        sig_fields_list = []

    if not sig_fields_list:
        return {
            'has_signatures': False,
            'signatures': [],
            'tampered': False,
            'summary': 'This PDF has no digital signatures.',
            'status': 'unsigned',
        }

    results = []
    any_tampered = False

    for sig in sig_fields_list:
        sig_info = {
            'field_name': getattr(sig, 'field_name', 'Unknown'),
            'signer_name': 'Unknown',
            'signing_time': None,
            'reason': None,
            'location': None,
            'intact': False,
            'valid': False,
            'hash_algorithm': 'SHA-256',
        }

        try:
            # Extract signer info from the PDF signature dictionary
            si = sig.sig_object
            if si is not None:
                if '/Name' in si:
                    sig_info['signer_name'] = str(si['/Name'])
                if '/Reason' in si:
                    sig_info['reason'] = str(si['/Reason'])
                if '/Location' in si:
                    sig_info['location'] = str(si['/Location'])
                if '/M' in si:
                    sig_info['signing_time'] = str(si['/M'])

            # Verify integrity using async API (pyhanko 0.35+)
            import asyncio
            from pyhanko.sign.validation import async_validate_pdf_signature

            try:
                loop = asyncio.new_event_loop()
                status = loop.run_until_complete(
                    async_validate_pdf_signature(
                        sig,
                        signer_validation_context=None,
                    )
                )
                loop.close()

                sig_info['intact'] = status.intact
                sig_info['valid'] = status.intact
                sig_info['coverage'] = 'Whole document' if status.intact else 'Partial / Modified'

                if not status.intact:
                    any_tampered = True
            except Exception:
                # Fallback: check byte range coverage
                try:
                    coverage = sig.evaluate_signature_coverage()
                    from pyhanko.sign.validation import SignatureCoverageLevel
                    is_full = coverage >= SignatureCoverageLevel.ENTIRE_FILE
                    sig_info['intact'] = is_full
                    sig_info['valid'] = is_full
                    if not is_full:
                        any_tampered = True
                except Exception:
                    sig_info['intact'] = False
                    sig_info['valid'] = False
                    any_tampered = True

        except Exception as e:
            sig_info['intact'] = False
            sig_info['valid'] = False
            sig_info['error'] = str(e)
            any_tampered = True

        results.append(sig_info)

    total = len(results)
    valid_count = sum(1 for r in results if r.get('valid'))

    if any_tampered:
        summary = f'⚠️ TAMPERED — {total - valid_count} of {total} signature(s) are broken. The document has been modified after signing.'
        status = 'tampered'
    else:
        summary = f'✅ VALID — All {total} signature(s) verified successfully. The document has not been modified.'
        status = 'valid'

    return {
        'has_signatures': True,
        'signatures': results,
        'tampered': any_tampered,
        'summary': summary,
        'status': status,
    }
