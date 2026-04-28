# CafeMate

A multilingual, mood-aware cafe ordering chatbot powered by **Azure OpenAI** and integrated with **Telegram**. Talk to it like a friend — it recommends drinks based on how you're feeling, takes orders in natural language, handles checkout & payments, and speaks your language.

## Features

- **Friend-like barista persona** — casual, warm, supportive conversation
- **Mood-based drink recommendations** — detects emotion from your messages and suggests the perfect drink
- **LLM-native intent detection** — Azure OpenAI classifies intent (order, remove, menu, checkout, chat, agree) via structured tags instead of brittle keyword matching
- **Natural language ordering** — "I want a Matcha Latte", "how about a Cold Brew?", "im thinking trying the Rose Latte" all work
- **Smart removal** — "remove the Americano", "I only want the Rose Latte", "skip the Hot Chocolate"
- **Multilingual** — replies naturally in Indonesian, Chinese, Japanese, Korean, English, and Spanish via Azure OpenAI native language detection
- **Full ordering flow** — browse menu, add items, remove items, view order, checkout, pay, rate & review
- **Payment support** — QR code and Virtual Account payment methods with inline confirmation buttons
- **Kitchen integration** — notifies back-kitchen group on new orders, sends pickup notification to customer when ready
- **Feedback collection** — star rating + optional comment, persisted to JSON
- **Session timeout** — auto-resets and sends timeout message after 60 seconds of inactivity post-ordering
- **Telegram integration** — works as a Telegram bot via polling or webhooks with inline keyboards
- **Owner admin panel** — manage the drink menu directly from Telegram with conversational wizards
- **JSON menu storage** — menu persists to `data/menu.json`, editable by hand or via bot commands

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Azure OpenAI (GPT-4o) |
| Framework | FastAPI + Uvicorn |
| Telegram | Webhook + python-telegram-bot style polling |
| Language detection | Azure OpenAI native + lightweight heuristic fallback |
| Config | `pydantic-settings` + `.env` |
| Language | Python 3.13 |
| Package Manager | `uv` |

## Project Structure

```
.
├── cafebot/
│   ├── __init__.py          # Package exports
│   ├── config.py            # Settings from .env
│   ├── engine.py            # Core chatbot logic, ordering flow, admin wizards
│   ├── feedback_manager.py  # JSON feedback persistence
│   ├── i18n.py              # Translations & lightweight language detection
│   ├── llm.py               # Azure OpenAI async client with intent tag protocol
│   ├── menu.py              # Menu data + multilingual mood keywords
│   ├── menu_manager.py      # Load/save menu JSON
│   └── models.py            # Drink, OrderItem, UserState dataclasses
├── data/
│   ├── menu.json            # Editable drink menu
│   └── feedback.json        # Persisted customer feedback
├── main.py                  # FastAPI app (webhook mode)
├── run_cli.py               # Local terminal testing
├── run_telegram.py          # Telegram polling mode
├── .env                     # Environment variables
├── pyproject.toml           # Dependencies
└── README.md
```

## Setup

### 1. Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Azure OpenAI resource (for multilingual AI responses)
- Telegram bot (via [@BotFather](https://t.me/botfather))

### 2. Clone & Install

```bash
git clone <repo-url>
cd hackathon
uv sync
```

### 3. Configure Environment

Copy `.env` and fill in your credentials:

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Telegram
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
WEBHOOK_SECRET=your-webhook-secret
WEBHOOK_URL=https://your-domain.com/webhook  # leave empty for polling mode

# Cafe owner (get your ID from @userinfobot)
OWNER_TELEGRAM_ID=123456789

# Kitchen group (get group ID by adding @userinfobot to the group)
KITCHEN_GROUP_ID=-1001234567890

# App
APP_PORT=8000
APP_HOST=0.0.0.0
```

> **Note:** If Azure OpenAI credentials are missing, the bot falls back to English-only local mode with keyword-based mood detection.

## How to Run

### Option A: Telegram Polling (easiest for local testing)

```bash
uv run python run_telegram.py
```

Open your bot on Telegram and send `/start`. The bot actively polls Telegram for messages.

### Option B: FastAPI Webhook (for production)

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

Then set your webhook:
```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<YOUR_URL>/webhook"
```

### Option C: Local CLI (for quick testing)

```bash
uv run python run_cli.py
```

## Using the Bot

### Customer Flow

| Step | What you do | What happens |
|---|---|---|
| 1 | Send `/start` | Bot greets you |
| 2 | Chat naturally | "I am feeling tired" → bot recommends Espresso |
| 3 | Order a drink | "I want a Matcha Latte" → added to order |
| 4 | Add more | Tap "Add Another Drink" → menu shown directly |
| 5 | Remove | "remove the Americano" or "I only want the Matcha" |
| 6 | Checkout | Tap "Checkout" or say "that's all" |
| 7 | Pay | Choose QR or Virtual Account, confirm payment |
| 8 | Pickup | Kitchen notifies you when ready, tap "Received" |
| 9 | Rate | Give 1-5 stars, optionally add a comment |

### Natural Language Examples

**Ordering:**
- "I want a Matcha Latte"
- "can I get an Americano?"
- "im thinking trying the Rose Latte"
- "how about a Cold Brew"
- "Rose Latte sounds good"

**Removing:**
- "remove the Americano"
- "skip the Hot Chocolate"
- "I don't want the Cold Brew anymore"
- "I only want the Rose Latte" (removes everything else)

**Menu & Order:**
- "what do you have?"
- "show me the menu"
- "my order"
- "what did I order?"

**Checkout:**
- "checkout"
- "that's all"
- "done for today"
- "I'm ready to pay"

### Inline Action Buttons

Action buttons appear contextually — only after you add or remove a drink:

- **Add Another Drink** — shows menu directly
- **Checkout** — proceeds to payment

### Session Timeout

After completing the full flow (order → checkout → payment → pickup → rating/feedback), if you don't interact for **60 seconds**, the bot automatically sends a timeout message and resets your session. You'll need to type `/start` to begin again.

### Owner Admin Commands

| Command | Description |
|---|---|
| `/admin` | Show admin help |
| `/admin_menu` | View full menu with details |
| `/admin_add` | Start conversational wizard to add a drink |
| `/admin_remove <name>` | Remove a drink |
| `/admin_reload` | Reload menu from `data/menu.json` |
| `/admin_cancel` | Cancel current wizard |
| `/admin_feedback` | View customer feedback summary |

#### Adding a Drink (Wizard)

```
You: /admin_add
Bot: Let's add a new drink! I'll ask a few questions.
     Type /admin_cancel anytime to abort.

     Question 1/6: What is the drink name?

You: Mocha
Bot: Got it: Mocha
     Question 2/6: What is the description?

You: Chocolate + espresso bliss
Bot: Nice!
     Question 3/6: What moods is this drink for?
     (comma-separated, e.g.: tired, stressed, happy)

You: happy, tired
Bot: Great!
     Question 4/6: What is the caffeine level?
     Options: none, low, medium, high

You: medium
Bot: Got it!
     Question 5/6: What is the temperature?
     Options: hot, iced, either

You: either
Bot: Almost there!
     Question 6/6: What is the price? (e.g. 5.50)

You: 5.75
Bot: Done! 'Mocha' has been added to the menu.
```

## Multilingual Support

With **Azure OpenAI** configured, the bot detects your language automatically and replies naturally. No need to set a language — just start chatting.

| Language | Example Input |
|---|---|
| Indonesian | "Saya merasa sangat lelah hari ini" / "mau pesan Matcha Latte" |
| Chinese | "我今天很累" / "我想要一杯美式咖啡" |
| Japanese | "疲れた" / "抹茶ラテをください" |
| Korean | "피곤해" / "아메리카노 주세요" |
| English | "I am feeling stressed" / "I want a Cold Brew" |
| Spanish | "Estoy muy cansado" / "Quiero un Matcha Latte" |

The system prompt instructs Azure OpenAI to keep drink names in English (e.g., Espresso, Matcha Latte) while speaking naturally in the user's language.

## Menu Data Format

Menu items are stored in `data/menu.json`:

```json
[
  {
    "name": "Espresso",
    "description": "A bold, concentrated shot of pure coffee energy.",
    "moods": ["tired", "exhausted", "sleepy"],
    "caffeine_level": "high",
    "temperature": "hot",
    "price": 3.50
  }
]
```

Fields:
- `name` — drink name (keep in English for consistency)
- `description` — shown to customers
- `moods` — keywords that trigger this recommendation
- `caffeine_level` — `none`, `low`, `medium`, `high`
- `temperature` — `hot`, `iced`, `either`
- `price` — number

## Architecture

```
User (Telegram/CLI/HTTP)
    ↓
run_telegram.py  │  main.py (FastAPI)  │  run_cli.py
    ↓                    ↓                    ↓
    └──────────────── CafeBotEngine ─────────────────┘
              ├─ AzureLLMClient (Azure OpenAI)
              │   ├─ Intent classification [INTENT:order|DRINK:xxx]
              │   ├─ Language detection [LANG:xx]
              │   └─ Natural response generation
              ├─ Pre-LLM intent fallback (remove/order constraints)
              ├─ Mood detection (multilingual keywords)
              ├─ Drink recommendation
              ├─ Order management (add/remove/checkout)
              ├─ Payment handling (QR / Virtual Account)
              ├─ Kitchen notifications
              ├─ Feedback collection
              ├─ Session timeout (60s auto-reset)
              └─ Admin wizards
                         ↓
              data/menu.json (persistent storage)
              data/feedback.json (customer feedback)
```

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | Recommended | Azure OpenAI resource URL |
| `AZURE_OPENAI_API_KEY` | Recommended | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Recommended | Model deployment name |
| `TELEGRAM_BOT_TOKEN` | For Telegram | From @BotFather |
| `OWNER_TELEGRAM_ID` | For admin | Your Telegram user ID |
| `KITCHEN_GROUP_ID` | For kitchen | Your Back Kitchen Group ID |
| `WEBHOOK_URL` | For webhook mode | Public HTTPS URL |
| `WEBHOOK_SECRET` | Optional | Webhook verification token |

## License

MIT
