# CafeMate

A multilingual, mood-aware cafe ordering chatbot powered by **Azure OpenAI** and integrated with **Telegram**. Talk to it like a friend — it recommends drinks based on how you're feeling, takes orders, and speaks your language.

## Features

- **Friend-like barista persona** — casual, warm, supportive conversation
- **Mood-based drink recommendations** — detects emotion from your messages and suggests the perfect drink
- **Multilingual** — replies naturally in Indonesian, Chinese, Japanese, Korean, English, and more via Azure OpenAI
- **Full ordering flow** — browse menu, add items, view order, checkout
- **Telegram integration** — works as a Telegram bot via polling or webhooks
- **Owner admin panel** — manage the drink menu directly from Telegram with conversational wizards
- **JSON menu storage** — menu persists to `data/menu.json`, editable by hand or via bot commands

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Azure OpenAI (GPT-4o) |
| Framework | FastAPI + Uvicorn |
| Telegram | python-telegram-bot style polling + webhook |
| Language detection | `langdetect` |
| Config | `pydantic-settings` + `.env` |
| Language | Python 3.13 |
| Package Manager | `uv` |

## Project Structure

```
.
├── cafebot/
│   ├── __init__.py          # Package exports
│   ├── config.py            # Settings from .env
│   ├── engine.py            # Core chatbot logic, admin wizards
│   ├── i18n.py              # Language detection
│   ├── llm.py               # Azure OpenAI async client
│   ├── menu.py              # Menu data + multilingual mood keywords
│   ├── menu_manager.py      # Load/save menu JSON
│   └── models.py            # Drink, OrderItem, UserState dataclasses
├── data/
│   └── menu.json            # Editable drink menu
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

### Customer Commands

| Command | Description |
|---|---|
| `/start` | Begin conversation with status banner |
| `menu` | View drink menu |
| `my order` | View current order |
| `checkout` | Complete order |
| Natural chat | "I am feeling tired" → gets Espresso recommendation |

### Owner Admin Commands

| Command | Description |
|---|---|
| `/admin` | Show admin help |
| `/admin_menu` | View full menu with details |
| `/admin_add` | Start conversational wizard to add a drink |
| `/admin_remove <name>` | Remove a drink |
| `/admin_reload` | Reload menu from `data/menu.json` |
| `/admin_cancel` | Cancel current wizard |

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

With **Azure OpenAI** configured, the bot detects your language and replies naturally:

| Language | Example Input |
|---|---|
| Indonesian | "Saya merasa sangat lelah hari ini" |
| Chinese | "我今天很累" |
| Japanese | "疲れた" |
| Korean | "피곤해" |
| English | "I am feeling stressed" |

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
              ├─ detect_language()
              ├─ AzureLLMClient (Azure OpenAI)
              ├─ Mood detection (multilingual keywords)
              ├─ Drink recommendation
              ├─ Order management
              └─ Admin wizards
                         ↓
              data/menu.json (persistent storage)
```

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | Recommended | Azure OpenAI resource URL |
| `AZURE_OPENAI_API_KEY` | Recommended | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Recommended | Model deployment name |
| `TELEGRAM_BOT_TOKEN` | For Telegram | From @BotFather |
| `OWNER_TELEGRAM_ID` | For admin | Your Telegram user ID |
| `WEBHOOK_URL` | For webhook mode | Public HTTPS URL |
| `WEBHOOK_SECRET` | Optional | Webhook verification token |

## License

MIT
