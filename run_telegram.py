"""Telegram polling runner — easiest way to test locally without webhooks."""

import asyncio
import sys

import httpx

from cafebot import CafeBotEngine, settings

BOT_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
engine = CafeBotEngine()


async def get_updates(client: httpx.AsyncClient, offset: int = 0) -> list[dict]:
    url = f"{BOT_API}/getUpdates"
    resp = await client.get(
        url,
        params={
            "offset": offset,
            "limit": 10,
            "timeout": 30,
            "allowed_updates": '["message","edited_message","callback_query"]',
        },
    )
    data = resp.json()
    return data.get("result", [])


async def send_message(client: httpx.AsyncClient, chat_id: int, text: str, reply_markup: dict | None = None, parse_mode: str = "Markdown") -> None:
    url = f"{BOT_API}/sendMessage"
    # Telegram has a 4096 char limit per message
    chunks = [text[i : i + 4000] for i in range(0, len(text), 4000)]
    for i, chunk in enumerate(chunks):
        payload = {"chat_id": chat_id, "text": chunk, "parse_mode": parse_mode}
        if i == len(chunks) - 1 and reply_markup:
            payload["reply_markup"] = reply_markup
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            # Fallback: retry without parse_mode in case Markdown caused the error
            payload.pop("parse_mode", None)
            await client.post(url, json=payload)


async def answer_callback(client: httpx.AsyncClient, callback_query_id: str) -> None:
    url = f"{BOT_API}/answerCallbackQuery"
    await client.post(url, json={"callback_query_id": callback_query_id})


async def send_photo(client: httpx.AsyncClient, chat_id: int, photo_path: str) -> None:
    url = f"{BOT_API}/sendPhoto"
    with open(photo_path, "rb") as f:
        await client.post(url, files={"photo": f}, data={"chat_id": chat_id})


async def edit_message_remove_buttons(client: httpx.AsyncClient, chat_id: int, message_id: int) -> None:
    """Remove inline keyboard from a message to prevent double-presses."""
    url = f"{BOT_API}/editMessageReplyMarkup"
    await client.post(url, json={"chat_id": chat_id, "message_id": message_id, "reply_markup": {}})


async def send_order_ready(client: httpx.AsyncClient, chat_id: int, user_id: str) -> None:
    """Send 'order ready' message with pickup confirmation button after a delay."""
    await asyncio.sleep(15)  # Simulate preparation time
    reply_markup = {
        "inline_keyboard": [
            [{"text": "✅ Received", "callback_data": f"pickup:{user_id}"}]
        ]
    }
    await send_message(
        client, chat_id,
        "Great news! Your order is ready for pickup. Please confirm once you've received it!",
        reply_markup=reply_markup,
    )


async def process_update(client: httpx.AsyncClient, update: dict) -> None:
    # Handle callback queries (inline keyboard button presses)
    callback_query = update.get("callback_query")
    if callback_query:
        data = callback_query.get("data", "")
        query_id = callback_query["id"]
        from_user = callback_query["from"]
        user_id = str(from_user["id"])
        chat_id = callback_query["message"]["chat"]["id"]

        await answer_callback(client, query_id)

        if data.startswith("pickup:"):
            reply = engine.confirm_pickup(user_id)
            await send_message(client, chat_id, reply)
            print(f"  -> Pickup confirmed by {user_id}")
            # Send rating buttons
            rating_markup = engine.get_rating_buttons(user_id)
            await send_message(client, chat_id, "How was your experience? Please rate us:", reply_markup=rating_markup)
            print(f"  -> Sent rating buttons to {user_id}")
        elif data.startswith("payment:"):
            method = data.split(":", 1)[1]
            reply = await engine.chat(user_id, method)
            await send_message(client, chat_id, reply)
            print(f"  -> Payment method selected: {method}")
            # If user paid via QR, send the QR code image + scan button
            qr_path = engine.get_payment_qr_path(user_id)
            if qr_path:
                await send_photo(client, chat_id, qr_path)
                print(f"  -> Sent QR code image to {user_id}")
            if engine.get_checkout_state(user_id) == "awaiting_qr_scan":
                scan_markup = {
                    "inline_keyboard": [
                        [{"text": "✅ I've Scanned", "callback_data": f"qr_scanned:{user_id}"}]
                    ]
                }
                await send_message(client, chat_id, "Tap the button after you scan the QR code:", reply_markup=scan_markup)
                print(f"  -> Sent QR scan button to {user_id}")
            if engine.get_checkout_state(user_id) == "awaiting_va_transfer":
                va_markup = {
                    "inline_keyboard": [
                        [{"text": "✅ I've Paid", "callback_data": f"va_paid:{user_id}"}]
                    ]
                }
                await send_message(client, chat_id, "Tap the button after you complete the transfer:", reply_markup=va_markup)
                print(f"  -> Sent VA paid button to {user_id}")
            # If user just placed an order, schedule delayed "ready for pickup" notification
            if engine.get_checkout_state(user_id) == "order_placed":
                asyncio.create_task(send_order_ready(client, chat_id, user_id))
                print(f"  -> Scheduled order ready notification for {user_id}")
        elif data.startswith("qr_scanned:"):
            reply = engine.confirm_qr_payment(user_id)
            await send_message(client, chat_id, reply)
            print(f"  -> QR payment confirmed by {user_id}")
            # Schedule delayed "ready for pickup" notification
            asyncio.create_task(send_order_ready(client, chat_id, user_id))
            print(f"  -> Scheduled order ready notification for {user_id}")
        elif data.startswith("va_paid:"):
            reply = engine.confirm_va_payment(user_id)
            await send_message(client, chat_id, reply)
            print(f"  -> VA payment confirmed by {user_id}")
            # Schedule delayed "ready for pickup" notification
            asyncio.create_task(send_order_ready(client, chat_id, user_id))
            print(f"  -> Scheduled order ready notification for {user_id}")
        elif data.startswith("order_add:"):
            await send_message(client, chat_id, "What would you like to add?")
            print(f"  -> Add another drink requested by {user_id}")
        elif data.startswith("order_checkout:"):
            reply = await engine.checkout(user_id)
            await send_message(client, chat_id, reply)
            print(f"  -> Checkout triggered by {user_id}")
            # If user is at checkout, send payment method buttons
            if engine.get_checkout_state(user_id) == "awaiting_payment":
                payment_markup = {
                    "inline_keyboard": [
                        [{"text": "🏦 Virtual Account", "callback_data": "payment:va"}],
                        [{"text": "📱 QR Code", "callback_data": "payment:qr"}],
                    ]
                }
                await send_message(client, chat_id, "Choose your payment method:", reply_markup=payment_markup)
                print(f"  -> Sent payment buttons to {user_id}")
        elif data.startswith("rating:"):
            parts = data.split(":")
            rating = int(parts[1])
            reply = engine.save_rating(user_id, rating)
            await send_message(client, chat_id, reply)
            print(f"  -> Rating {rating}/5 received from {user_id}")
        # Remove buttons from the original message to prevent double-presses
        message_id = callback_query["message"]["message_id"]
        await edit_message_remove_buttons(client, chat_id, message_id)
        return

    message_obj = update.get("message") or update.get("edited_message")
    if not message_obj:
        return

    text = message_obj.get("text", "").strip()
    chat_id = message_obj["chat"]["id"]
    user_id = str(message_obj["from"]["id"])
    user_from = message_obj["from"]
    name = user_from.get("first_name") or user_from.get("username")

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
        reply = await engine.greet(user_id, name=name)
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
    elif lower == "/admin_feedback":
        reply = engine.admin_get_feedback() if engine.is_owner(user_id) else "Access denied. This command is for the cafe owner only."
    elif lower == "/admin_cancel":
        reply = engine.admin_cancel_wizard(user_id) if engine.is_owner(user_id) else "Access denied. This command is for the cafe owner only."
    else:
        reply = await engine.chat(user_id, text, name=name)

    await send_message(client, chat_id, reply)
    print(f"  -> Replied ({len(reply)} chars)")

    # If user has order items, send Add Another / Checkout action buttons
    action_buttons = engine.get_order_action_buttons(user_id)
    if action_buttons:
        await send_message(client, chat_id, "What would you like to do next?", reply_markup=action_buttons)
        print(f"  -> Sent order action buttons to {user_id}")

    # If user is at checkout, send payment method buttons
    if engine.get_checkout_state(user_id) == "awaiting_payment":
        payment_markup = {
            "inline_keyboard": [
                [{"text": "🏦 Virtual Account", "callback_data": "payment:va"}],
                [{"text": "📱 QR Code", "callback_data": "payment:qr"}],
            ]
        }
        await send_message(
            client, chat_id,
            "Choose your payment method:",
            reply_markup=payment_markup,
        )
        print(f"  -> Sent payment buttons to {user_id}")

    # If user paid via QR, send the QR code image
    qr_path = engine.get_payment_qr_path(user_id)
    if qr_path:
        await send_photo(client, chat_id, qr_path)
        print(f"  -> Sent QR code image to {user_id}")

    # If user just placed an order, schedule delayed "ready for pickup" notification
    if engine.get_checkout_state(user_id) == "order_placed":
        asyncio.create_task(send_order_ready(client, chat_id, user_id))
        print(f"  -> Scheduled order ready notification for {user_id}")


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
