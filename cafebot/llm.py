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

    def _system_prompt(self, user_name: str | None = None, lang_hint: str = "en") -> str:
        drinks = ", ".join(d.name for d in DRINK_MENU)
        name_hint = f" The customer's name is {user_name}. Use their name naturally once in a while. " if user_name else ""
        lang = language_name(lang_hint)
        return (
            "You are CafeMate, a warm, friendly barista who talks to customers like they're your close friend. "
            "You work at a cozy cafe and your superpower is recommending the perfect drink based on how someone feels. "
            "Keep responses short (1-3 sentences max), casual, warm, and supportive. Use occasional lowercase and conversational tone. "
            "Never be robotic. Be the kind of friend who remembers your order and asks how they're REALLY doing. "
            f"Today's date is {datetime.now().strftime('%A, %B %d')}. "
            f"Available drinks: {drinks}. "
            f"{name_hint}"
            f"CRITICAL LANGUAGE RULE: The user's current message is written in {lang}. "
            f"You MUST reply entirely in {lang}. "
            "Analyze ONLY the latest user message to determine the language. "
            "Do NOT let previous messages in the conversation history influence your language choice. "
            "Even if earlier messages were in a different language, always respond in the language of the CURRENT user message. "
            "Do not translate drink names — keep them in English (e.g., Espresso, Matcha Latte). "
            "But all other text (greetings, explanations, friendly banter) must be in the user's detected language. "
            "IMPORTANT: When a user explicitly mentions a drink by name, the system will add it to their order. "
            "If you recommend a drink and they agree with words like 'sure', 'ok', or 'yes', the system will also add it. "
            "After a drink is added, acknowledge it warmly and show their current order. "
            "If they want to finish and pay, they can say things like 'I'm done', 'let's pay', or 'checkout' and the system will handle it. "
            "Guide them naturally: after adding a drink, ask if they want anything else or if they're ready to pay."
        )

    async def chat(
        self,
        message: str,
        history: list[dict],
        user_name: str | None = None,
        system_override: str | None = None,
        max_tokens: int = 150,
        lang_hint: str = "en",
    ) -> str:
        if not self._client:
            return ""
        system_prompt = system_override if system_override else self._system_prompt(user_name, lang_hint)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        # Prepend language instruction directly on the user message for stronger compliance
        lang_prefix = f"[Respond in {lang}] "
        messages.append({"role": "user", "content": lang_prefix + message})
        try:
            response = await self._client.chat.completions.create(
                model=settings.azure_openai_deployment_name,
                messages=messages,
                temperature=0.9,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            # Silently fail so engine falls back to local mode
            logging.debug("Azure LLM error: %s", e)
            return ""
