"""Language name utilities (langdetect removed — Azure OpenAI handles detection natively)."""

# ISO 639-1 -> friendly language name for display / logging
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


def language_name(code: str) -> str:
    """Get friendly language name for display / logging."""
    return _LANG_NAMES.get(code, _LANG_NAMES.get(code.split("-")[0], "English"))