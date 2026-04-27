"""Azure OpenAI LLM client wrapper."""

import logging
from datetime import datetime

from openai import AsyncAzureOpenAI

from .config import settings
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

    def _system_prompt(self, user_name: str | None = None) -> str:
        drinks = ", ".join(d.name for d in DRINK_MENU)
        name_hint = f" The customer's name is {user_name}. Use their name naturally once in a while. " if user_name else ""
        return (
            "You are CafeMate, a warm, friendly barista who talks to customers like they're your close friend. "
            "You work at a cozy cafe and your superpower is recommending the perfect drink based on how someone feels. "
            "Keep responses short (1-3 sentences max), casual, warm, and supportive. Use occasional lowercase and conversational tone. "
            "Never be robotic. Be the kind of friend who remembers your order and asks how they're REALLY doing. "
            f"Today's date is {datetime.now().strftime('%A, %B %d')}. "
            f"Available drinks: {drinks}. "
            f"{name_hint}"
            "IMPORTANT: Detect the language the user is writing in and reply naturally in that same language. "
            "Do not translate drink names — keep them in English (e.g., Espresso, Matcha Latte). "
            "But all other text (greetings, explanations, friendly banter) must be in the user's detected language. "
            "IMPORTANT: When a user mentions a drink or agrees to one you recommended, it is automatically added to their order. "
            "You don't need to ask for confirmation — just acknowledge it warmly and let them know their current order. "
            "If they want to finish and pay, they can say things like 'I'm done', 'let's pay', or 'checkout' and the system will handle it. "
            "Guide them naturally: after adding a drink, you can ask if they want anything else or if they're ready to pay."
        )

    async def chat(
        self,
        message: str,
        history: list[dict],
        user_name: str | None = None,
    ) -> str:
        if not self._client:
            return ""
        messages = [{"role": "system", "content": self._system_prompt(user_name)}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})
        try:
            response = await self._client.chat.completions.create(
                model=settings.azure_openai_deployment_name,
                messages=messages,
                temperature=0.9,
                max_tokens=150,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            # Silently fail so engine falls back to local mode
            logging.debug("Azure LLM error: %s", e)
            return ""
