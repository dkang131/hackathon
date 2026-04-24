"""Telegram polling runner — easiest way to test locally without webhooks."""

import asyncio
import sys

import httpx

from cafebot import CafeBotEngine, settings

BOT_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
engine = CafeBotEngine()


async def get_updates(client: httpx.AsyncClient, offset: int = 0) -> list[dict]:
    url = f"{BOT_API}/getUpdates"
    resp = await client.get(url, params={"offset": offset, "limit": 10, "timeout": 30})
    data = resp.json()
    return data.get("result", [])


async def send_message(client: httpx.AsyncClient, chat_id: int, text: str) -> None:
    url = f"{BOT_API}/sendMessage"
    # Telegram has a 4096 char limit per message
    chunks = [text[i : i + 4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        await client.post(url, json={"chat_id": chat_id, "text": chunk})


async def process_update(client: httpx.AsyncClient, update: dict) -> None:
    message_obj = update.get("message") or update.get("edited_message")
    if not message_obj:
        return

    text = message_obj.get("text", "").strip()
    chat_id = message_obj["chat"]["id"]
    user_id = str(message_obj["from"]["id"])

    if not text:
        return

    print(f"[{user_id}] {text}")

    # Check if user is in an admin wizard first
    wizard_reply = engine.handle_admin_wizard(user_id, text)
    if wizard_reply:
        await send_message(client, chat_id, wizard_reply)
        print(f"  -> Wizard reply ({len(wizard_reply)} chars)")
        return

    # Route commands
    lower = text.lower()
    if lower == "/start":
        reply = await engine.greet(user_id)
    elif lower in ["/admin", "/admin_help"]:
        reply = engine.admin_help(user_id) if engine.is_owner(user_id) else "Access denied. This command is for the cafe owner only."
    elif lower == "/admin_menu":
        reply = engine.admin_view_menu() if engine.is_owner(user_id) else "Access denied. This command is for the cafe owner only."
    elif lower == "/admin_add":
        if engine.is_owner(user_id):
            reply = engine.admin_start_add_wizard(user_id)
        else:
            reply = "Access denied. This command is for the cafe owner only."
    elif lower.startswith("/admin_remove "):
        if engine.is_owner(user_id):
            reply = engine.admin_remove_drink(text[len("/admin_remove "):].strip())
        else:
            reply = "Access denied. This command is for the cafe owner only."
    elif lower == "/admin_reload":
        reply = engine.admin_reload_menu() if engine.is_owner(user_id) else "Access denied. This command is for the cafe owner only."
    elif lower == "/admin_cancel":
        reply = engine.admin_cancel_wizard(user_id) if engine.is_owner(user_id) else "Access denied. This command is for the cafe owner only."
    else:
        reply = await engine.chat(user_id, text)

    await send_message(client, chat_id, reply)
    print(f"  -> Replied ({len(reply)} chars)")


async def main() -> None:
    if not settings.telegram_bot_token or settings.telegram_bot_token.startswith("your-"):
        print("Error: TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    print("=" * 60)
    print("  CafeMate Telegram Polling Mode")
    print(f"  Bot token: ...{settings.telegram_bot_token[-6:]}")
    print(f"  Owner ID:  {settings.owner_telegram_id or 'Not set'}")
    print(f"  Azure LLM: {'Connected' if engine._llm.available else 'Fallback (English only)'}")
    print("=" * 60)
    print("  Send /start to your bot on Telegram to begin!")
    print("  Press Ctrl+C to stop")
    print("-" * 60)

    offset = 0
    async with httpx.AsyncClient() as client:
        while True:
            try:
                updates = await get_updates(client, offset)
                for update in updates:
                    offset = update["update_id"] + 1
                    await process_update(client, update)
                if not updates:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n\nShutting down...")
                break
            except Exception as e:
                print(f"[Error] {e}")
                await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
