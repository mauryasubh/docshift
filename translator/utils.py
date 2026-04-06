"""
translator/utils.py — argostranslate, fully offline.
Patches StanzaSentencizer directly in argostranslate.sbd so it never
calls stanza.Pipeline and never tries to download from GitHub.
"""
import re


def _patch():
    """
    Patch argostranslate.sbd.StanzaSentencizer to use simple regex splitting.
    Must be called before get_installed_languages() is ever called.
    """
    try:
        import argostranslate.sbd as sbd

        class _SimpleSentencizer:
            """
            Drop-in replacement for StanzaSentencizer.
            Accepts any arguments (pkg, lang_code, etc.) and ignores them.
            Never downloads anything from the internet.
            """
            def __init__(self, *args, **kwargs):
                pass  # accept pkg or any other arg, do nothing

            def split_sentences(self, text):
                # Simple regex sentence splitting — works offline
                parts = re.split(r'(?<=[.!?])\s+', text.strip())
                return [p for p in parts if p.strip()] or [text]

        # Replace the class in the module
        sbd.StanzaSentencizer = _SimpleSentencizer

        # Also patch Sentencizer factory function if it exists
        if hasattr(sbd, 'Sentencizer'):
            _orig_sentencizer = sbd.Sentencizer
            def _patched_sentencizer(*args, **kwargs):
                return _SimpleSentencizer()
            sbd.Sentencizer = _patched_sentencizer

        # Also patch SBDSentencizer if it exists
        if hasattr(sbd, 'SBDSentencizer'):
            sbd.SBDSentencizer = _SimpleSentencizer

        print('[translator] argostranslate SBD patched — offline mode active')

    except Exception as e:
        print(f'[translator] patch warning: {e}')


# Apply patch at import time — before anything else runs
_patch()


def translate_text(text, source='auto', target='en', **kwargs):
    """Translate text using argostranslate — fully offline."""
    if not text or not text.strip():
        return text

    try:
        # Re-apply patch in case Celery worker reimported the module
        _patch()

        src = source if source != 'auto' else _detect_lang(text)
        if src == target:
            return text

        from argostranslate import translate
        installed = translate.get_installed_languages()
        lang_map  = {l.code: l for l in installed}

        if src not in lang_map:
            raise RuntimeError(
                f"Model '{src}' not installed.\n"
                f"Run: python -c \"import argostranslate.package; "
                f"argostranslate.package.install_from_path("
                f"r'C:\\\\path\\\\to\\\\translate-{src}_{target}-1_9.argosmodel')\""
            )
        if target not in lang_map:
            raise RuntimeError(f"Model '{target}' not installed.")

        translation = lang_map[src].get_translation(lang_map[target])
        if translation is None:
            raise RuntimeError(f"No model for {src}→{target}.")

        return translation.translate(text)

    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Translation error: {e}")


def _detect_lang(text):
    french = ['le ', 'la ', 'les ', 'un ', 'une ', 'des ', 'du ',
              'est ', 'sont ', 'avec ', 'pour ', 'dans ', 'que ',
              'qui ', 'sur ', 'par ', 'au ', 'aux ', 'en ', 'ce ',
              'se ', 'ne ', 'pas ', 'mais ', 'et ', 'je ', 'il ']
    score = sum(1 for w in french if w in text.lower())
    return 'fr' if score >= 2 else 'en'


def chunk_text(text, max_chars=400):
    if len(text) <= max_chars:
        return [text]
    chunks, current = [], ''
    for sentence in re.split(r'(?<=[.!?])\s+', text):
        if len(current) + len(sentence) > max_chars and current:
            chunks.append(current.strip())
            current = sentence + ' '
        else:
            current += sentence + ' '
    if current.strip():
        chunks.append(current.strip())
    return chunks or [text]


def translate_long_text(text, source='auto', target='en'):
    if not text or not text.strip():
        return text
    return ' '.join(
        translate_text(chunk, source, target)
        for chunk in chunk_text(text)
    )


def get_available_languages():
    try:
        _patch()
        from argostranslate import translate
        return [
            {'code': l.code, 'name': l.name,
             'targets': [t.to_lang.code for t in l.translations_from]}
            for l in translate.get_installed_languages()
        ]
    except Exception:
        return []


def check_language_pair(source, target):
    if source == 'auto':
        return True, ''
    try:
        _patch()
        from argostranslate import translate
        installed = translate.get_installed_languages()
        if not installed:
            return False, "No translation models installed."
        lang_map = {l.code: l for l in installed}
        if source not in lang_map:
            return False, f"Model for '{source}' not installed."
        targets = [t.to_lang.code for t in lang_map[source].translations_from]
        if target not in targets:
            return False, f"No model for {source}→{target}."
        return True, ''
    except Exception:
        return True, ''
