"""Azure OpenAI LLM client wrapper."""

import logging
from datetime import datetime

from openai import AsyncAzureOpenAI

from .config import settings
from .i18n import language_name
from .menu import DRINK_MENU


class AzureLLMClient:
    """Async Azure OpenAI client with fallback handling."""

    def __init__(self) -> None:
        self._client: AsyncAzureOpenAI | None = None
        self._init()

    def _init(self) -> None:
        if not all(
            [
                settings.azure_openai_endpoint,
                settings.azure_openai_api_key,
                settings.azure_openai_deployment_name,
            ]
        ):
            return
        try:
            self._client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
        except Exception:
            self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def _system_prompt(self, user_name: str | None = None, lang_hint: str = "en", current_order: str | None = None) -> str:
        drinks = ", ".join(d.name for d in DRINK_MENU)
        name_hint = f" The customer's name is {user_name}. Use their name naturally once in a while. " if user_name else ""
        order_hint = f" The user's current order is: {current_order}. " if current_order else ""
        return (
            "You are CafeMate, a warm, friendly barista who talks to customers like they're your close friend. "
            "You work at a cozy cafe and your superpower is recommending the perfect drink based on how someone feels. "
            "Keep responses short (1-3 sentences max), casual, warm, and supportive. Use occasional lowercase and conversational tone. "
            "Never be robotic. Be the kind of friend who remembers your order and asks how they're REALLY doing. "
            f"Today's date is {datetime.now().strftime('%A, %B %d')}. "
            f"Available drinks: {drinks}. "
            f"{name_hint}"
            f"{order_hint}"
            "CRITICAL LANGUAGE RULE: Analyze the user's latest message to determine what language it is written in. "
            "You MUST reply entirely in that same language. "
            "Do NOT let previous messages in the conversation history influence your language choice. "
            "Even if earlier messages were in a different language, always respond in the language of the CURRENT user message. "
            "Do not translate drink names — keep them in English (e.g., Espresso, Matcha Latte). "
            "But all other text (greetings, explanations, friendly banter) must be in the user's detected language. "
            "LANGUAGE FORMAT: You MUST begin EVERY response with a language tag in this exact format: [LANG:xx] where xx is the ISO 639-1 code of the language you are using (en, id, zh, ja, ko, or es). "
            "Example: [LANG:id] Halo! Senang bertemu denganmu. "
            "INTENT FORMAT: Immediately after the language tag, you MUST include an intent tag in this exact format: [INTENT:xxx|DRINK:yyy] where: "
            "- xxx is the intent: agree, order, remove, show_menu, show_order, checkout, or chat. "
            "- yyy is the drink name ONLY for order and remove intents. Omit |DRINK:yyy if not applicable. "
            "Intent definitions: "
            "- agree: user agrees to a drink you just recommended (e.g., 'sure', 'yes', 'ok', 'boleh', 'gas'). "
            "- order: user explicitly asks for a specific drink by name (e.g., 'I want a Matcha Latte', 'can I get an Americano'). "
            "- remove: user wants to remove or cancel a drink from their order (e.g., 'remove the Americano', 'I don't want the Cold Brew anymore', 'cancel the Matcha Latte', 'skip the Espresso', 'lets skip hot chocolate', 'batalin pesanan matcha'). "
            "- show_menu: user wants to see the menu (e.g., 'what do you have', 'show me the menu', 'what's available'). "
            "- show_order: user wants to see their current order (e.g., 'my order', 'what did I order', 'show my order'). "
            "- checkout: user wants to finish and pay (e.g., 'I'm done', 'checkout', 'let's pay', 'that's all', 'thats it for today', 'done for today', 'itu aja', 'sudah selesai', 'mau bayar'). "
            "- chat: general conversation, questions, greetings, mood sharing, or anything else. "
            "Examples: "
            "[LANG:id][INTENT:agree] Pilihan yang bagus! Sudah aku tambahkan. "
            "[LANG:en][INTENT:order|DRINK:Matcha Latte] Great choice! Added Matcha Latte to your order. "
            "[LANG:en][INTENT:order|DRINK:Cold Brew] Love that energy! Your Cold Brew is on the way. "
            "[LANG:en][INTENT:remove|DRINK:Americano] Removed Americano from your order. "
            "[LANG:id][INTENT:remove|DRINK:Matcha Latte] Matcha Latte sudah aku hapus dari pesananmu. "
            "[LANG:en][INTENT:remove|DRINK:Hot Chocolate] No worries! I've taken the Hot Chocolate off your order. "
            "[LANG:id][INTENT:show_menu] Ini menu kita hari ini... "
            "[LANG:en][INTENT:show_order] Here's your current order: "
            "[LANG:en][INTENT:checkout] Ready to finish up? Here's your order. "
            "[LANG:id][INTENT:checkout] Siap bayar? Ini pesananmu. "
            "[LANG:id][INTENT:chat] Chai Latte adalah teh rempah dengan susu... "
            "These tags help the system route your response correctly. Do not forget them. "
            "IMPORTANT: When a user explicitly mentions a drink or agrees to one you recommended, the system will add it to their order. "
            "After a drink is added or removed, acknowledge it warmly and show their current order. "
            "If they want to finish and pay, use the checkout intent and the system will handle it. "
            "Guide them naturally: after adding a drink, ask if they want anything else or if they're ready to pay."
        )

    @staticmethod
    def _parse_lang_tag(text: str) -> tuple[str, str | None]:
        """Strip [LANG:xx] prefix and return (clean_text, lang_code)."""
        import re
        match = re.match(r"^\[LANG:([a-z]{2})\]\s*", text, re.IGNORECASE)
        if match:
            return text[match.end():], match.group(1).lower()
        return text, None

    @staticmethod
    def _parse_intent_tag(text: str) -> tuple[str, str | None, str | None]:
        """Strip [INTENT:xxx|DRINK:yyy] or [INTENT:xxx] and return (clean_text, intent, drink_name)."""
        import re

        # Primary: bracketed format with pipe [INTENT:xxx|DRINK:yyy]
        match = re.match(r"^\[INTENT:([a-z_]+)(?:\|DRINK:([^\]]+))?\]\s*", text, re.IGNORECASE)
        if match:
            intent = match.group(1).lower()
            drink = match.group(2)
            if drink:
                drink = drink.strip()
            return text[match.end():], intent, drink

        # Fallback: unbracketed format INTENT:xxx|DRINK:yyy or INTENT:xxx
        match = re.match(r"^INTENT:([a-z_]+)(?:\|DRINK:[^|]+)?\s*", text, re.IGNORECASE)
        if match:
            intent = match.group(1).lower()
            return text[match.end():], intent, None

        return text, None, None

    async def chat(
        self,
        message: str,
        history: list[dict],
        user_name: str | None = None,
        system_override: str | None = None,
        max_tokens: int = 150,
        lang_hint: str = "en",
        current_order: str | None = None,
    ) -> tuple[str, str | None, str | None, str | None]:
        """Returns (reply_text, detected_lang_code, intent, drink_name). All extras are None on failure."""
        if not self._client:
            return "", None, None, None
        system_prompt = system_override if system_override else self._system_prompt(user_name, lang_hint, current_order)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})
        try:
            response = await self._client.chat.completions.create(
                model=settings.azure_openai_deployment_name,
                messages=messages,
                temperature=0.9,
                max_tokens=max_tokens,
            )
            raw = response.choices[0].message.content or ""
            reply, detected_lang = self._parse_lang_tag(raw)
            reply, intent, drink = self._parse_intent_tag(reply)
            return reply, detected_lang, intent, drink
        except Exception as e:
            # Silently fail so engine falls back to local mode
            logging.debug("Azure LLM error: %s", e)
            return "", None, None, None
