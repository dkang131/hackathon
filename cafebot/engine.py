"""Core async chatbot engine — user-stateful, Azure-backed."""

import random
import time
from datetime import datetime

from .models import Drink, OrderItem, UserState
from .menu import DRINK_MENU, MOOD_KEYWORDS
from .menu_manager import load_menu, save_menu
from .llm import AzureLLMClient
from .config import settings
from .feedback_manager import add_feedback, get_feedback_summary, update_last_feedback_comment
from .i18n import detect_language_simple, t

# ---- Friendly response pools ----
_GREETINGS = [
    "Hey there! Welcome to my little corner of caffeinated joy. I'm your barista buddy today! What's going on in your world?",
    "Hiiii! So glad you stopped by. Grab a virtual seat and tell me — how's your day treating you?",
    "Welcome, welcome! This is your safe space for good drinks and zero judgment. What's the vibe today?",
]

_FOLLOW_UPS = [
    "Oh, I totally get that. Want me to whip up something perfect for exactly that mood?",
    "Hmm, I feel you. You know what? I have JUST the thing. Wanna hear it?",
    "Aww, thanks for sharing that with me. Let me recommend something that'll hit the spot.",
    "I hear you loud and clear. One special drink coming right up in conversation form!",
]

_CONFIRMATIONS = [
    "Yes, great choice! I can already picture you sipping that.",
    "Ooh, wonderful pick! That's going to be perfect for you.",
    "Love that choice! You've got great taste, friend.",
    "Done and done! That's one of my favorites too.",
]

_SMALL_TALK = [
    "By the way, have you tried any new cafes lately? I'm always scouting for inspo!",
    "Fun fact: I judge all drinks by how good they'd taste on a rainy day with a good playlist.",
    "If you could have any superpower while drinking coffee, what would it be? I'd choose never-burned-tongue.",
    "Honestly, the best part of this job? Seeing someone's face light up when they take that first sip.",
]

_FAREWELLS = [
    "Aww, you're leaving? Come back soon, okay? Your next drink is already waiting in my imagination!",
    "Take care out there, friend! Hope that drink makes your day a little brighter.",
    "Byeee! Remember: whatever you're going through, you've got this. And you've got good coffee too now!",
]

_MOOD_RESPONSES: dict[str, list[str]] = {
    "tired": [
        "Oh no, you sound beat! {rec}\n  Sounds like exactly what you need right now, yeah?",
        "Tired days are the WORST. Let me help. {rec}\n  Wanna give it a shot?",
    ],
    "stressed": [
        "Hey, deep breath. You're doing great. {rec}\n  Sometimes you just need a little sweetness, y'know?",
        "Stress is temporary, but good drinks are forever. {rec}\n  This one's on my recommendation list for tough days.",
    ],
    "sad": [
        "Aww, sending you a big virtual hug. {rec}\n  Sometimes you just need something warm and comforting, right?",
        "I'm really sorry you're feeling down. {rec}\n  It won't fix everything, but it might make the next hour a little better.",
    ],
    "frustrated": [
        "Ugh, that's so annoying. I get it. {rec}\n  Something grounding and calming to reset your mood?",
        "Frustration sucks. Let's channel it into trying something new. {rec}\n  Matcha always chills me out.",
    ],
    "bored": [
        "Boredom = opportunity for adventure! {rec}\n  This'll wake up your taste buds at least!",
        "Let's spice things up then! {rec}\n  Way more exciting than another plain water, right?",
    ],
    "nostalgic": [
        "Nostalgia hits different sometimes. {rec}\n  This one always takes me back to cozy afternoons.",
        "Memory lane is a nice place to visit. {rec}\n  It's like a warm hug from the past.",
    ],
    "confident": [
        "YESSS, I love that energy! {rec}\n  Keep that momentum going, champ!",
        "You're absolutely crushing it! {rec}\n  The perfect fuel for someone on their A-game.",
    ],
    "happy": [
        "Yay, happy vibes are contagious! {rec}\n  Let's celebrate that good energy!",
        "Your joy just made my day! {rec}\n  Something a little special for a special mood!",
    ],
    "sick": [
        "Oh no, feel better soon! {rec}\n  This one's basically a warm, tasty medicine.",
        "Being sick is the worst. {rec}\n  Get cozy and sip this slowly, okay?",
    ],
    "playful": [
        "I love this energy! {rec}\n  Let's make it a fun one!",
        "Playful moods deserve playful drinks! {rec}\n  Chewy pearls = instant joy.",
    ],
}


class CafeBotEngine:
    """Async bot engine. Keeps per-user state in memory (swap for Redis / Cosmos DB for scale)."""

    def __init__(self) -> None:
        self._users: dict[str, UserState] = {}
        self._llm = AzureLLMClient()

    # ---------- state management ----------

    def _get_state(self, user_id: str) -> UserState:
        if user_id not in self._users:
            self._users[user_id] = UserState(user_id=user_id)
        return self._users[user_id]

    def _clear_user(self, user_id: str) -> None:
        self._users.pop(user_id, None)

    # ---------- session timeout ----------

    TIMEOUT_SECONDS = 60

    def _update_activity(self, user_id: str) -> None:
        self._get_state(user_id).last_activity = time.time()

    def _reset_state(self, user_id: str) -> None:
        state = self._get_state(user_id)
        preserved_name = state.user_name
        preserved_lang = state.lang_hint
        self._users[user_id] = UserState(user_id=user_id, user_name=preserved_name, lang_hint=preserved_lang)

    def _maybe_reset(self, user_id: str) -> bool:
        state = self._get_state(user_id)
        if state.last_activity == 0:
            return False
        elapsed = time.time() - state.last_activity
        if elapsed > self.TIMEOUT_SECONDS:
            # Only reset if order is empty and not awaiting feedback (flow completed)
            if not state.order and not state.awaiting_feedback:
                self._reset_state(user_id)
                return True
        return False

    def check_and_reset_timeout(self, user_id: str) -> str | None:
        """Check if user has timed out. If so, reset state and return timeout message."""
        state = self._get_state(user_id)
        if state.last_activity == 0:
            return None
        elapsed = time.time() - state.last_activity
        if elapsed > self.TIMEOUT_SECONDS:
            if not state.order and not state.awaiting_feedback:
                lang = state.lang_hint
                self._reset_state(user_id)
                return t("session_timeout", lang)
        return None

    # ---------- helpers ----------

    @staticmethod
    def _detect_mood(text: str) -> str | None:
        text_lower = text.lower()
        scores: dict[str, int] = {}
        for mood, keywords in MOOD_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score:
                scores[mood] = score
        return max(scores, key=scores.get) if scores else None

    @staticmethod
    def _recommend_for_mood(mood: str | None) -> Drink:
        if mood:
            matches = [d for d in DRINK_MENU if mood in d.moods]
            if matches:
                return random.choice(matches)
        return random.choice(DRINK_MENU)

    @staticmethod
    def _format_drink(drink: Drink) -> str:
        temps = {"hot": "steaming hot", "iced": "ice-cold", "either": "just the way you like it"}
        caffeine = {"none": "caffeine-free", "low": "lightly caffeinated", "medium": "moderately caffeinated", "high": "highly caffeinated"}
        return (
            f"How about a *{drink.name}*? It's {temps[drink.temperature]} and {caffeine[drink.caffeine_level]}.\n"
            f"  {drink.description}\n"
            f"  Price: ${drink.price:.2f}"
        )

    def _get_lang(self, user_id: str) -> str:
        """Return cached language hint for user."""
        return self._get_state(user_id).lang_hint

    @staticmethod
    def _render_menu(lang: str = "en") -> str:
        lines = [t("menu_title", lang)]
        for d in DRINK_MENU:
            lines.append(f"• {d.name} — ${d.price:.2f} ({d.caffeine_level} caffeine, {d.temperature})")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _render_order(state: UserState) -> str:
        lang = state.lang_hint
        if not state.order:
            return t("order_empty", lang)
        total = sum(i.drink.price * i.quantity for i in state.order)
        lines = [t("order_title", lang)]
        for i in state.order:
            lines.append(f"• {i.quantity}× {i.drink.name} — ${i.drink.price * i.quantity:.2f}")
        lines.append(t("total", lang, total=total))
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _try_parse_order(text: str) -> str | None:
        lower = text.lower()
        # Exact substring match first
        for drink in DRINK_MENU:
            if drink.name.lower() in lower:
                return drink.name
        # Fuzzy match: every drink word must match a text word (substring in either direction)
        text_words = lower.split()
        for drink in DRINK_MENU:
            drink_words = drink.name.lower().split()
            matched = 0
            for dw in drink_words:
                for tw in text_words:
                    if dw in tw or tw in dw:
                        if len(tw) >= 3 or len(dw) >= 3:
                            matched += 1
                            break
            if matched >= len(drink_words) * 0.6:
                return drink.name
        return None

    # ---------- core logic ----------

    async def greet(self, user_id: str, name: str | None = None) -> str:
        state = self._get_state(user_id)
        if name:
            state.user_name = name

        self._update_activity(user_id)
        user_name = state.user_name
        status_lines = [
            "CafeMate is online!",
            f"User: {user_name}" if user_name else "",
            # f"Azure OpenAI: {'Connected' if self._llm.available else 'Offline (English fallback)'}",
            f"Menu items: {len(DRINK_MENU)}",
            "Available Languages: Indonesian, Chinese, Japanese, Korean, English, Spanish",
            "\n",
        ]
        if self._llm.available:
            greet_prompt = (
                f"Say a warm, friendly greeting to {user_name}, a new customer. "
                if user_name
                else "Say a warm, friendly greeting to a new customer. "
            ) + "Ask how they're doing today."
            reply, detected_lang, _intent, _drink = await self._llm.chat(
                greet_prompt,
                state.conversation_history,
                user_name=user_name,
                lang_hint=state.lang_hint,
            )
            if reply:
                if detected_lang:
                    state.lang_hint = detected_lang
                state.conversation_history.append({"role": "user", "content": "Say a warm, friendly greeting to a new customer. Ask how they're doing today."})
                state.conversation_history.append({"role": "assistant", "content": reply})
                return "\n".join(status_lines) + reply
        fallback = random.choice(_GREETINGS)
        if user_name:
            fallback = f"Hey {user_name}! {fallback}"
        return "\n".join(status_lines) + fallback

    async def chat(self, user_id: str, message: str, name: str | None = None) -> str:
        """Main entry — returns the bot's reply for the given user & message."""
        state = self._get_state(user_id)
        if name:
            state.user_name = name

        # Update activity timestamp
        self._update_activity(user_id)

        # Detect and cache user language from their message
        detected = detect_language_simple(message)
        if detected != "en":
            state.lang_hint = detected
        lang = state.lang_hint

        # --- feedback handling ---
        if state.awaiting_feedback:
            state.feedback_history.append(message)
            state.awaiting_feedback = False
            comment = message.strip()
            if comment.lower() not in ("done", "no", "none", "n/a", "-", "selesai", "完成", "完了", "완료"):
                update_last_feedback_comment(user_id, comment)
            if state.feedback_rating:
                stars = "⭐" * state.feedback_rating
                return (
                    f"{t('thanks_feedback', lang)}\n\n"
                    f"Rating: {stars} ({state.feedback_rating}/5)"
                )
            return t("thanks_feedback", lang)

        # --- payment selection during checkout ---
        if state.checkout_state == "awaiting_payment":
            return await self._handle_payment(user_id, message)

        # --- lightweight pre-LLM fallback for remove commands ---
        lower = message.lower()
        if any(kw in lower for kw in ["remove", "ilangkan", "hapus", "delete", "batal", "batalin", "kurangi", "kurang", "cancel", "skip", "don't want", "dont want", "tidak mau", "ga mau", "nggak mau"]):
            to_remove = self._try_parse_order(message)
            if to_remove:
                drink = next((d for d in DRINK_MENU if d.name.lower() == to_remove.lower()), None)
                if drink:
                    for i, item in enumerate(state.order):
                        if item.drink.name.lower() == drink.name.lower():
                            state.order.pop(i)
                            state.last_recommended = None
                            state.show_action_buttons = True
                            return f"{t('removed', lang, name=drink.name)}\n{self._render_order(state)}"
                    return f"{t('not_in_order', lang, name=drink.name)}\n{self._render_order(state)}"
            state.last_recommended = None
            return "No problem! Let me know if you want something else."

        # --- lightweight pre-LLM fallback for obvious order commands ---
        ordered = self._try_parse_order(message)
        if ordered:
            # Only auto-order if it looks like a simple request, not a question or constraint
            is_question = "?" in message or any(kw in lower for kw in ["what is", "what's", "how is", "how are", "bagaimana", "berapa", "apa itu", "do you have", "is there", "can you make", "why", "kenapa"])
            has_order_intent = any(kw in lower for kw in ["want", "get", "try", "have", "like", "thinking", "go with", "sounds good", "add", "order", "please", "do", "get me", "ill have", "i'll have", "can i", "could i", "may i", "give me", "mau", "pesan", "boleh", "iya", "ya", "gas", "about", "let's", "lets", "pick", "choose", "go for", "feeling like", "craving"])
            has_constraint = any(kw in lower for kw in ["only", "just", "instead", "not", "don't", "dont", "no", "tidak", "bukan", "ga", "nggak", "remove", "delete", "cancel", "skip", "batal", "hapus", "ilangkan", "kurangi", "kurang", "change", "ganti", "ubah"])
            if not is_question and has_order_intent and not has_constraint:
                drink = next((d for d in DRINK_MENU if d.name.lower() == ordered.lower()), None)
                if drink:
                    state.order.append(OrderItem(drink))
                    state.last_recommended = None
                    state.show_action_buttons = True
                    return f"{t('confirmation', lang)}\n{self._render_order(state)}"

        # --- LLM intent classification + routing ---
        if self._llm.available:
            order_context = ", ".join(f"{i.quantity}x {i.drink.name}" for i in state.order) if state.order else "empty"
            reply, detected_lang, intent, drink_name = await self._llm.chat(
                message,
                state.conversation_history,
                user_name=state.user_name,
                lang_hint=lang,
                current_order=order_context,
            )
            if reply or intent:
                if detected_lang:
                    state.lang_hint = detected_lang
                    lang = detected_lang

                state.conversation_history.append({"role": "user", "content": message})
                state.conversation_history.append({"role": "assistant", "content": reply})

                # Route based on LLM-classified intent
                if intent == "agree" and state.last_recommended:
                    state.order.append(OrderItem(state.last_recommended))
                    state.last_recommended = None
                    state.show_action_buttons = True
                    return f"{reply}\n\n{self._render_order(state)}\n"

                if intent == "order":
                    target_drink = drink_name or self._try_parse_order(message)
                    if target_drink:
                        drink = next((d for d in DRINK_MENU if d.name.lower() == target_drink.lower()), None)
                        if drink:
                            state.order.append(OrderItem(drink))
                            state.last_recommended = None
                            state.show_action_buttons = True
                            return f"{reply}\n\n{self._render_order(state)}\n"
                    state.show_action_buttons = False
                    return reply

                if intent == "remove":
                    target_drink = drink_name or self._try_parse_order(message)
                    if target_drink:
                        drink = next((d for d in DRINK_MENU if d.name.lower() == target_drink.lower()), None)
                        if drink:
                            for i, item in enumerate(state.order):
                                if item.drink.name.lower() == drink.name.lower():
                                    state.order.pop(i)
                                    state.show_action_buttons = True
                                    return f"{reply}\n\n{self._render_order(state)}\n"
                            state.show_action_buttons = True
                            return f"{reply}\n\n{t('not_in_order', lang, name=drink.name)}\n{self._render_order(state)}"
                    state.show_action_buttons = False
                    return reply

                if intent == "show_menu":
                    state.show_action_buttons = False
                    return reply  # LLM generates conversational menu response

                if intent == "show_order":
                    state.show_action_buttons = False
                    return f"{reply}\n\n{self._render_order(state)}"

                if intent == "checkout":
                    state.show_action_buttons = False
                    return await self._checkout(user_id)

                # Default / chat intent — set last_recommended if LLM mentions a drink
                # but only if user isn't clearly trying to remove, checkout, or see menu
                state.show_action_buttons = False
                if not any(kw in lower for kw in ["remove", "ilangkan", "hapus", "delete", "batal", "batalin", "kurangi", "kurang", "cancel", "skip", "don't want", "dont want", "tidak mau", "ga mau", "nggak mau", "checkout", "pay", "done", "finish", "menu", "what do you have", "what's available", "my order"]):
                    for drink in DRINK_MENU:
                        if drink.name.lower() in reply.lower():
                            state.last_recommended = drink
                            break
                return reply

        # --- local fallback (last resort only) ---
        return self._local_response(message)

    def _local_response(self, message: str) -> str:
        mood = self._detect_mood(message)
        drink = self._recommend_for_mood(mood)
        rec = self._format_drink(drink)

        if mood and mood in _MOOD_RESPONSES:
            template = random.choice(_MOOD_RESPONSES[mood])
            return template.format(rec=rec)

        generic = [
            f"Hmm, I'm picking up on some vibes but not totally sure what's up. {rec}\n  Wanna try this? It's a crowd favorite!",
            f"You know what? No matter the mood, this is always a good call: {rec}\n  Sound good?",
            random.choice(_SMALL_TALK),
        ]
        return random.choice(generic)

    def _generate_va_number(self, user_id: str) -> str:
        """Generate a mock virtual account number."""
        import hashlib
        seed = hashlib.md5(f"{user_id}-cafe-mate-va".encode()).hexdigest()[:10]
        return f"88099{seed}"

    def _generate_qr_code(self, user_id: str, amount: float) -> str:
        """Generate a mock QR code image and return the file path."""
        import os
        import qrcode
        data = f"https://cafe-mate.mock/pay?user={user_id}&amount={amount:.2f}&ref=CAFEMATE"
        img = qrcode.make(data)
        os.makedirs("data", exist_ok=True)
        path = f"data/qr_{user_id}.png"
        img.save(path)
        return path

    async def _checkout(self, user_id: str) -> str:
        state = self._get_state(user_id)
        lang = state.lang_hint
        if not state.order:
            return t("no_order", lang)
        if state.checkout_state == "awaiting_payment":
            return (
                f"{self._render_order(state)}\n"
                f"{t('choose_payment', lang)}"
            )
        receipt = self._render_order(state)
        state.checkout_state = "awaiting_payment"
        return f"{receipt}\n"

    async def _handle_payment(self, user_id: str, message: str) -> str:
        """Handle payment selection — now button-driven, but callbacks route through here."""
        state = self._get_state(user_id)
        lang = state.lang_hint
        selected = message.strip().lower()

        if selected not in ("va", "qr"):
            return t("choose_payment", lang)

        total = sum(i.drink.price * i.quantity for i in state.order)
        state.payment_method = selected.upper()
        state.paid_amount = total

        if selected == "va":
            state.checkout_state = "awaiting_va_transfer"
            va_number = self._generate_va_number(user_id)
            return (
                f"{t('total', lang, total=total)}\n\n"
                f"{t('pay_va', lang, va=va_number)}"
            )
        # QR
        state.checkout_state = "awaiting_qr_scan"
        qr_path = self._generate_qr_code(user_id, total)
        return (
            f"{t('total', lang, total=total)}\n\n"
            f"{t('pay_qr', lang)}"
        )

    async def checkout(self, user_id: str) -> str:
        """Public wrapper to trigger checkout for a user."""
        self._update_activity(user_id)
        return await self._checkout(user_id)

    def get_order_action_buttons(self, user_id: str) -> dict | None:
        """Return Add Another / Checkout buttons if user has items and isn't in checkout flow."""
        state = self._get_state(user_id)
        lang = state.lang_hint
        if state.show_action_buttons and state.order and state.checkout_state is None and not state.last_recommended:
            state.show_action_buttons = False
            return {
                "inline_keyboard": [
                    [
                        {"text": t("add_another", lang), "callback_data": f"order_add:{user_id}"},
                        {"text": t("checkout_btn", lang), "callback_data": f"order_checkout:{user_id}"},
                    ]
                ]
            }
        return None

    def confirm_qr_payment(self, user_id: str) -> str:
        """Confirm QR payment scan and move to order_placed state."""
        self._update_activity(user_id)
        state = self._get_state(user_id)
        lang = state.lang_hint
        if state.checkout_state != "awaiting_qr_scan":
            return "Hmm, I don't see a pending QR payment."
        state.checkout_state = "order_placed"
        return t("payment_received", lang)

    def confirm_va_payment(self, user_id: str) -> str:
        """Confirm VA payment transfer and move to order_placed state."""
        self._update_activity(user_id)
        state = self._get_state(user_id)
        lang = state.lang_hint
        if state.checkout_state != "awaiting_va_transfer":
            return "Hmm, I don't see a pending VA transfer."
        state.checkout_state = "order_placed"
        return t("payment_received", lang)

    def get_kitchen_order_message(self, user_id: str) -> str:
        """Format order details for the kitchen group."""
        state = self._get_state(user_id)
        if not state.order:
            return ""
        total = sum(i.drink.price * i.quantity for i in state.order)
        lines = [f"🍽️ *New Order* — User: {state.user_name or user_id}"]
        for i in state.order:
            lines.append(f"• {i.quantity}× {i.drink.name}")
        lines.append(f"_Total: ${total:.2f}_")
        return "\n".join(lines)

    def get_kitchen_ready_button(self, user_id: str) -> dict:
        """Return inline keyboard for kitchen to mark order ready."""
        return {
            "inline_keyboard": [
                [{"text": "✅ Mark as Ready", "callback_data": f"kitchen_ready:{user_id}"}]
            ]
        }

    def kitchen_mark_ready(self, user_id: str) -> str:
        """Mark order as ready by kitchen — returns message for user."""
        state = self._get_state(user_id)
        lang = state.lang_hint
        if state.checkout_state != "order_placed":
            return ""
        return t("order_ready", lang)

    def get_payment_qr_path(self, user_id: str) -> str | None:
        """Return QR code image path if user paid via QR."""
        state = self._get_state(user_id)
        if state.payment_method == "QR":
            return f"data/qr_{user_id}.png"
        return None

    def get_checkout_state(self, user_id: str) -> str | None:
        """Get current checkout state for a user."""
        state = self._get_state(user_id)
        return state.checkout_state

    def confirm_pickup(self, user_id: str) -> str:
        """Mark order as picked up and clear state."""
        self._update_activity(user_id)
        state = self._get_state(user_id)
        lang = state.lang_hint
        state.order = []
        state.checkout_state = None
        state.payment_method = None
        state.paid_amount = 0.0
        state.awaiting_feedback = True
        state.feedback_rating = None
        return t("enjoy", lang)

    def save_rating(self, user_id: str, rating: int) -> str:
        """Save user rating to persistent JSON storage and prompt for optional comment."""
        self._update_activity(user_id)
        state = self._get_state(user_id)
        lang = state.lang_hint
        state.feedback_rating = rating
        state.feedback_history.append(f"Rating: {rating}/5")
        # Persist to JSON immediately
        add_feedback(
            user_id=user_id,
            user_name=state.user_name,
            rating=rating,
            comment="",
        )
        stars = "⭐" * rating
        return (
            f"{t('thanks_feedback', lang)}\n\n"
            f"Rating: {stars} ({rating}/5)\n\n"
            f"{t('rate_comment', lang)}"
        )

    def get_rating_buttons(self, user_id: str) -> dict:
        """Return inline keyboard for 1-5 star rating."""
        return {
            "inline_keyboard": [
                [
                    {"text": "1 ⭐", "callback_data": f"rating:1:{user_id}"},
                    {"text": "2 ⭐", "callback_data": f"rating:2:{user_id}"},
                    {"text": "3 ⭐", "callback_data": f"rating:3:{user_id}"},
                    {"text": "4 ⭐", "callback_data": f"rating:4:{user_id}"},
                    {"text": "5 ⭐", "callback_data": f"rating:5:{user_id}"},
                ]
            ]
        }

    async def farewell(self, user_id: str) -> str:
        state = self._get_state(user_id)
        if state.order:
            return f"Wait, you still have an order! {self._render_order(state)}\nType 'checkout' to finish up, or 'quit' again to cancel."
        self._clear_user(user_id)
        return random.choice(_FAREWELLS)

    # ---------- admin / owner commands ----------

    def is_owner(self, user_id: str) -> bool:
        """Check if user is the cafe owner."""
        if not settings.owner_telegram_id:
            return False
        return str(user_id) == settings.owner_telegram_id

    def admin_help(self, user_id: str = "") -> str:
        header = "Owner access confirmed!" if self.is_owner(user_id) else ""
        body = (
            "\n  --- Owner Commands ---\n"
            "  /admin_menu          - View current menu with details\n"
            "  /admin_add           - Add a drink (conversational wizard)\n"
            "  /admin_remove <name> - Remove a drink by name\n"
            "  /admin_reload        - Reload menu from file\n"
            "  /admin_feedback      - View all user feedback\n"
            "  /admin_cancel        - Cancel current wizard\n"
            "  ----------------------\n"
            "\n  To add a drink easily, just type /admin_add and follow the prompts."
        )
        return f"{header}{body}" if header else body

    def admin_view_menu(self) -> str:
        """Detailed menu view for the owner."""
        if not DRINK_MENU:
            return "Menu is empty! Add drinks with /admin_add"
        lines = ["\n  --- Menu (Owner View) ---"]
        for i, d in enumerate(DRINK_MENU, 1):
            lines.append(f"  {i}. {d.name}")
            lines.append(f"     ${d.price:.2f} | {d.caffeine_level} caffeine | {d.temperature}")
            lines.append(f"     {d.description}")
            lines.append(f"     Moods: {', '.join(d.moods)}")
        lines.append("  -------------------------\n")
        return "\n".join(lines)

    def admin_get_feedback(self) -> str:
        """Retrieve all persisted user feedback from JSON storage."""
        return get_feedback_summary()

    def admin_add_drink(self, json_str: str) -> str:
        """Add a drink from JSON string and persist."""
        import json
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {e}\n\nUse format:\n{{\"name\":\"...\", \"description\":\"...\", \"moods\":[\"tired\"], \"caffeine_level\":\"medium\", \"temperature\":\"hot\", \"price\":5.0}}"

        required = ["name", "description", "moods", "caffeine_level", "temperature", "price"]
        missing = [f for f in required if f not in data]
        if missing:
            return f"Missing fields: {', '.join(missing)}"

        # Check for duplicate
        if any(d.name.lower() == data["name"].lower() for d in DRINK_MENU):
            return f"'{data['name']}' already exists on the menu. Use /admin_remove first if you want to replace it."

        drink = Drink(
            name=data["name"],
            description=data["description"],
            moods=data["moods"],
            caffeine_level=data["caffeine_level"],
            temperature=data["temperature"],
            price=float(data["price"]),
        )
        DRINK_MENU.append(drink)
        save_menu(DRINK_MENU)
        return f"Added '{drink.name}' (${drink.price:.2f}) to the menu!"

    def admin_remove_drink(self, name: str) -> str:
        """Remove a drink by name and persist."""
        name = name.strip()
        if not name:
            return "Usage: /admin_remove <drink name>"
        idx = next((i for i, d in enumerate(DRINK_MENU) if d.name.lower() == name.lower()), None)
        if idx is None:
            return f"'{name}' not found on the menu."
        removed = DRINK_MENU.pop(idx)
        save_menu(DRINK_MENU)
        return f"Removed '{removed.name}' from the menu."

    def admin_reload_menu(self) -> str:
        """Reload menu from disk."""
        global DRINK_MENU
        DRINK_MENU.clear()
        DRINK_MENU.extend(load_menu())
        return f"Menu reloaded from file. {len(DRINK_MENU)} drinks available."

    # ---------- admin wizard (conversational add drink) ----------

    def admin_start_add_wizard(self, user_id: str) -> str:
        """Start the conversational add-drink wizard."""
        self._update_activity(user_id)
        state = self._get_state(user_id)
        state.admin_wizard = "add_drink"
        state.admin_wizard_data = {}
        return (
            "Let's add a new drink! I'll ask a few questions.\n"
            "Type /admin_cancel anytime to abort.\n\n"
            "Question 1/6: What is the drink name?"
        )

    def admin_cancel_wizard(self, user_id: str) -> str:
        """Cancel any active wizard."""
        self._update_activity(user_id)
        state = self._get_state(user_id)
        state.admin_wizard = None
        state.admin_wizard_data = {}
        return "Wizard cancelled. Nothing was saved."

    def handle_admin_wizard(self, user_id: str, message: str) -> str | None:
        """Handle a wizard step. Returns reply if in wizard, None otherwise."""
        self._update_activity(user_id)
        state = self._get_state(user_id)
        if state.admin_wizard != "add_drink":
            return None

        data = state.admin_wizard_data
        step = len(data)

        # Step 0: name
        if step == 0:
            name = message.strip()
            if not name:
                return "Please enter a valid name.\nQuestion 1/6: What is the drink name?"
            if any(d.name.lower() == name.lower() for d in DRINK_MENU):
                return f"'{name}' already exists. Try a different name or /admin_cancel."
            data["name"] = name
            return f"Got it: {name}\n\nQuestion 2/6: What is the description?"

        # Step 1: description
        if step == 1:
            desc = message.strip()
            if not desc:
                return "Please enter a description.\nQuestion 2/6: What is the description?"
            data["description"] = desc
            return (
                "Nice!\n\n"
                "Question 3/6: What moods is this drink for?\n"
                "(comma-separated, e.g.: tired, stressed, happy)"
            )

        # Step 2: moods
        if step == 2:
            moods = [m.strip().lower() for m in message.split(",") if m.strip()]
            if not moods:
                return "Please enter at least one mood.\nQuestion 3/6: What moods is this drink for?"
            data["moods"] = moods
            return (
                "Great!\n\n"
                "Question 4/6: What is the caffeine level?\n"
                "Options: none, low, medium, high"
            )

        # Step 3: caffeine_level
        if step == 3:
            level = message.strip().lower()
            if level not in ("none", "low", "medium", "high"):
                return "Please choose: none, low, medium, or high.\nQuestion 4/6: What is the caffeine level?"
            data["caffeine_level"] = level
            return (
                "Got it!\n\n"
                "Question 5/6: What is the temperature?\n"
                "Options: hot, iced, either"
            )

        # Step 4: temperature
        if step == 4:
            temp = message.strip().lower()
            if temp not in ("hot", "iced", "either"):
                return "Please choose: hot, iced, or either.\nQuestion 5/6: What is the temperature?"
            data["temperature"] = temp
            return "Almost there!\n\nQuestion 6/6: What is the price? (e.g. 5.50)"

        # Step 5: price
        if step == 5:
            try:
                price = float(message.strip())
                if price <= 0:
                    raise ValueError
            except ValueError:
                return "Please enter a valid price (e.g. 5.50).\nQuestion 6/6: What is the price?"
            data["price"] = price

            # All done — save the drink
            drink = Drink(
                name=data["name"],
                description=data["description"],
                moods=data["moods"],
                caffeine_level=data["caffeine_level"],
                temperature=data["temperature"],
                price=price,
            )
            DRINK_MENU.append(drink)
            save_menu(DRINK_MENU)

            # Clear wizard state
            state.admin_wizard = None
            state.admin_wizard_data = {}

            return (
                f"Done! '{drink.name}' has been added to the menu.\n"
                f"Price: ${drink.price:.2f} | Caffeine: {drink.caffeine_level} | Temp: {drink.temperature}\n"
                f"Moods: {', '.join(drink.moods)}\n\n"
                f"Use /admin_menu to see the full menu."
            )

        return None
