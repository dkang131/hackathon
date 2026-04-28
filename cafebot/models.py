"""Data models for CafeBot."""

from dataclasses import dataclass, field


@dataclass
class Drink:
    name: str
    description: str
    moods: list[str]
    caffeine_level: str  # none, low, medium, high
    temperature: str  # hot, iced, either
    price: float


@dataclass
class OrderItem:
    drink: Drink
    quantity: int = 1
    customizations: list[str] = field(default_factory=list)


@dataclass
class UserState:
    """Per-user conversation and order state."""

    user_id: str
    order: list[OrderItem] = field(default_factory=list)
    conversation_history: list[dict] = field(default_factory=list)
    user_name: str | None = None
    # Order confirmation
    pending_drink: Drink | None = None
    last_recommended: Drink | None = None

    # Checkout flow
    checkout_state: str | None = None  # "awaiting_payment", "order_placed"
    payment_method: str | None = None
    paid_amount: float = 0.0

    # Admin wizard state
    admin_wizard: str | None = None  # e.g. "add_drink"
    admin_wizard_data: dict = field(default_factory=dict)

    # Feedback state
    awaiting_feedback: bool = False
    feedback_rating: int | None = None
    feedback_history: list[str] = field(default_factory=list)

    # Language hint for localized order forms
    lang_hint: str = "en"

    # UI: whether to show Add Another / Checkout buttons on next response
    show_action_buttons: bool = False

    # Last activity timestamp for session timeout
    last_activity: float = 0.0
