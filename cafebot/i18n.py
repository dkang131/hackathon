"""Language detection utilities."""

from langdetect import detect_langs
from langdetect.lang_detect_exception import LangDetectException

# ISO 639-1 -> friendly language name for LLM prompts
_LANG_NAMES: dict[str, str] = {
    "en": "English",
    "id": "Indonesian",
    "ms": "Malay",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "th": "Thai",
    "vi": "Vietnamese",
    "tl": "Tagalog",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "pl": "Polish",
    "nl": "Dutch",
}

_DEFAULT_LANG = "en"


def detect_language(text: str) -> str:
    """Detect language code from text. Returns ISO 639-1 code (defaults to 'en')."""
    if not text or len(text.strip()) < 3:
        return _DEFAULT_LANG
    try:
        probs = detect_langs(text)
        if not probs:
            return _DEFAULT_LANG
        best = max(probs, key=lambda x: x.prob)
        if best.prob < 0.6:
            return _DEFAULT_LANG
        # langdetect often confuses casual English with Tagalog, and Indonesian with Tagalog
        if best.lang == "tl":
            id_prob = next((p.prob for p in probs if p.lang == "id"), 0.0)
            if id_prob > 0.2:
                return "id"
            if best.prob < 0.9:
                return _DEFAULT_LANG
        return best.lang
    except LangDetectException:
        return _DEFAULT_LANG


def language_name(code: str) -> str:
    """Get friendly language name for LLM prompts."""
    return _LANG_NAMES.get(code, _LANG_NAMES.get(code.split("-")[0], "English"))



