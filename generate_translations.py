"""
Auto-generate template translations using Azure OpenAI.

Usage:
    uv run python generate_translations.py <language_code>

Examples:
    uv run python generate_translations.py th    # Thai
    uv run python generate_translations.py vi    # Vietnamese
    uv run python generate_translations.py pt    # Portuguese
"""

import asyncio
import json
import sys

from cafebot.i18n import _TEMPLATES
from cafebot.llm import AzureLLMClient


SYSTEM_PROMPT = """You are a professional translator for a cafe chatbot called CafeMate.
Translate the given English strings into the target language. Follow these rules:

1. Keep Telegram Markdown formatting (*bold*, _italic_)
2. Keep emojis (☕, 💳, ✅, 🧾, etc.)
3. Keep placeholder variables like {total} and {va} exactly as-is
4. Keep button text SHORT (under 20 characters if possible)
5. Use a warm, friendly tone matching a barista
6. Return ONLY a JSON object mapping each key to its translation

Example output format:
{
  "confirmation": "...",
  "order_empty": "..."
}"""


async def generate_translations(lang_code: str, lang_name: str) -> dict[str, str]:
    """Use Azure OpenAI to translate all template keys into the target language."""
    llm = AzureLLMClient()
    if not llm.available:
        print("Error: Azure OpenAI is not configured. Check your .env file.")
        sys.exit(1)

    # Build the source texts
    sources = {key: texts["en"] for key, texts in _TEMPLATES.items()}
    prompt = (
        f"Translate these CafeMate bot strings into {lang_name} ({lang_code}).\n\n"
        f"Source strings (JSON):\n{json.dumps(sources, ensure_ascii=False, indent=2)}\n\n"
        f"Return ONLY the translations as a JSON object with the same keys."
    )

    print(f"Requesting translations from Azure OpenAI for {lang_name} ({lang_code})...")
    reply = await llm.chat(prompt, [], system_override=SYSTEM_PROMPT, max_tokens=2000)

    # Extract JSON from the response
    try:
        # Try to find JSON block
        if "```json" in reply:
            json_str = reply.split("```json")[1].split("```")[0].strip()
        elif "```" in reply:
            json_str = reply.split("```")[1].split("```")[0].strip()
        else:
            json_str = reply.strip()
        translations = json.loads(json_str)
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Error parsing LLM response: {e}")
        print("Raw response:")
        print(reply)
        sys.exit(1)

    return translations


def print_translation_block(lang_code: str, translations: dict[str, str]) -> None:
    """Print the translations in a format ready to paste into i18n.py."""
    print()
    print("=" * 60)
    print(f"  Generated translations for '{lang_code}'")
    print("=" * 60)
    print()
    print(f'    "{lang_code}": {{')
    for key, text in translations.items():
        escaped = text.replace('"', '\\"').replace('\n', '\\n')
        print(f'        "{key}": "{escaped}",')
    print("    },")
    print()
    print("Copy the block above into each template dict in cafebot/i18n.py")
    print("=" * 60)


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python generate_translations.py <language_code>")
        print("Examples:")
        print("  uv run python generate_translations.py th   # Thai")
        print("  uv run python generate_translations.py vi   # Vietnamese")
        print("  uv run python generate_translations.py pt   # Portuguese")
        sys.exit(1)

    lang_code = sys.argv[1].lower()

    # Language code to friendly name mapping
    lang_names = {
        "th": "Thai",
        "vi": "Vietnamese",
        "pt": "Portuguese",
        "tr": "Turkish",
        "pl": "Polish",
        "nl": "Dutch",
        "ar": "Arabic",
        "hi": "Hindi",
        "tl": "Tagalog",
        "ms": "Malay",
        "de": "German",
        "fr": "French",
        "it": "Italian",
        "ru": "Russian",
    }
    lang_name = lang_names.get(lang_code, lang_code.capitalize())

    translations = await generate_translations(lang_code, lang_name)
    print_translation_block(lang_code, translations)


if __name__ == "__main__":
    asyncio.run(main())
