"""
FastAPI app — webhook-ready for Telegram integration.

Run locally:
    uv run uvicorn main:app --reload

Or set webhook for Telegram:
    https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WEBHOOK_URL>/webhook
"""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
import asyncio

from cafebot import CafeBotEngine, settings
from cafebot.menu import DRINK_MENU
from cafebot.i18n import t

app = FastAPI(title="CafeMate", version="0.2.0")
engine = CafeBotEngine()


@app.get("/health")
async def health() -> dict:
    """Health check — also reports Azure LLM status."""
    return {
        "status": "ok",
        "azure_llm_available": engine._llm.available,
    }


@app.post("/chat")
async def chat_endpoint(request: Request) -> dict:
    """HTTP API for chatting with the bot (useful for testing / web frontend)."""
    body = await request.json()
    user_id = body.get("user_id", "anonymous")
    message = body.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message required")
    reply = await engine.chat(user_id, message)
    return {"user_id": user_id, "reply": reply}


# ---------- Admin HTTP endpoints (for testing / web dashboard) ----------


@app.get("/admin/menu")
async def admin_menu(request: Request) -> dict:
    """View full menu details (owner only — check owner_id param)."""
    owner_id = request.query_params.get("owner_id", "")
    if not engine.is_owner(owner_id) and settings.owner_telegram_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner only")
    return {"drinks": [
        {"name": d.name, "description": d.description, "moods": d.moods,
         "caffeine_level": d.caffeine_level, "temperature": d.temperature, "price": d.price}
        for d in DRINK_MENU
    ]}


@app.post("/admin/add")
async def admin_add(request: Request) -> dict:
    """Add a drink (owner only). Body: {\"owner_id\": \"...\", \"drink\": {...}}"""
    body = await request.json()
    owner_id = body.get("owner_id", "")
    if not engine.is_owner(owner_id) and settings.owner_telegram_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner only")
    import json
    result = engine.admin_add_drink(json.dumps(body.get("drink", {})))
    return {"result": result}


@app.delete("/admin/remove")
async def admin_remove(request: Request) -> dict:
    """Remove a drink by name (owner only). Body: {\"owner_id\": \"...\", \"name\": \"...\"}"""
    body = await request.json()
    owner_id = body.get("owner_id", "")
    if not engine.is_owner(owner_id) and settings.owner_telegram_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner only")
    result = engine.admin_remove_drink(body.get("name", ""))
    return {"result": result}


@app.post("/webhook")
async def telegram_webhook(request: Request) -> JSONResponse:
    """
    Telegram webhook endpoint.
    Expects Telegram Update JSON: https://core.telegram.org/bots/api#update
    """
    # Optional secret check
    if settings.webhook_secret:
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret != settings.webhook_secret:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    data = await request.json()

    # Handle callback queries (inline keyboard button presses)
    callback_query = data.get("callback_query")
    if callback_query:
        callback_data = callback_query.get("data", "")
        query_id = callback_query["id"]
        from_user = callback_query["from"]
        user_id = str(from_user["id"])
        chat_id = callback_query["message"]["chat"]["id"]

        # Answer callback to remove loading spinner
        import httpx
        answer_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/answerCallbackQuery"
        asyncio.create_task(
            _async_post(answer_url, {"callback_query_id": query_id})
        )

        if callback_data.startswith("pickup:"):
            reply = engine.confirm_pickup(user_id)
            asyncio.create_task(_send_telegram_message(chat_id, reply))
            # Send rating buttons
            lang = engine._get_lang(user_id)
            rating_markup = engine.get_rating_buttons(user_id)
            asyncio.create_task(_send_telegram_message(chat_id, t("feedback_prompt", lang), reply_markup=rating_markup))
        elif callback_data.startswith("payment:"):
            method = callback_data.split(":", 1)[1]
            reply = await engine.chat(user_id, method)
            asyncio.create_task(_send_telegram_message(chat_id, reply))
            # If user paid via QR, send the QR code image + scan button
            qr_path = engine.get_payment_qr_path(user_id)
            if qr_path:
                asyncio.create_task(_send_telegram_photo(chat_id, qr_path))
            if engine.get_checkout_state(user_id) == "awaiting_qr_scan":
                lang = engine._get_lang(user_id)
                scan_markup = {
                    "inline_keyboard": [
                        [{"text": t("paid_qr", lang), "callback_data": f"qr_scanned:{user_id}"}]
                    ]
                }
                asyncio.create_task(_send_telegram_message(chat_id, t("scan_qr_prompt", lang), reply_markup=scan_markup))
            if engine.get_checkout_state(user_id) == "awaiting_va_transfer":
                lang = engine._get_lang(user_id)
                va_markup = {
                    "inline_keyboard": [
                        [{"text": t("paid_va", lang), "callback_data": f"va_paid:{user_id}"}]
                    ]
                }
                asyncio.create_task(_send_telegram_message(chat_id, t("transfer_prompt", lang), reply_markup=va_markup))
        elif callback_data.startswith("qr_scanned:"):
            reply = engine.confirm_qr_payment(user_id)
            asyncio.create_task(_send_telegram_message(chat_id, reply))
            # Notify kitchen group
            asyncio.create_task(_send_kitchen_notification(user_id))
        elif callback_data.startswith("va_paid:"):
            reply = engine.confirm_va_payment(user_id)
            asyncio.create_task(_send_telegram_message(chat_id, reply))
            # Notify kitchen group
            asyncio.create_task(_send_kitchen_notification(user_id))
        elif callback_data.startswith("kitchen_ready:"):
            customer_id = callback_data.split(":", 1)[1]
            reply = engine.kitchen_mark_ready(customer_id)
            if reply:
                # Send pickup notification to the customer (not the staff member who clicked)
                user_chat = int(customer_id)
                lang = engine._get_lang(customer_id)
                pickup_markup = {
                    "inline_keyboard": [
                        [{"text": t("received_btn", lang), "callback_data": f"pickup:{customer_id}"}]
                    ]
                }
                asyncio.create_task(_send_telegram_message(user_chat, reply, reply_markup=pickup_markup))
        elif callback_data.startswith("order_add:"):
            lang = engine._get_lang(user_id)
            asyncio.create_task(_send_telegram_message(chat_id, t("add_prompt", lang)))
        elif callback_data.startswith("order_checkout:"):
            reply = await engine.checkout(user_id)
            asyncio.create_task(_send_telegram_message(chat_id, reply))
            # If user is at checkout, send payment method buttons
            if engine.get_checkout_state(user_id) == "awaiting_payment":
                lang = engine._get_lang(user_id)
                payment_markup = {
                    "inline_keyboard": [
                        [{"text": t("va_btn", lang), "callback_data": "payment:va"}],
                        [{"text": t("qr_btn", lang), "callback_data": "payment:qr"}],
                    ]
                }
                asyncio.create_task(_send_telegram_message(chat_id, t("choose_payment", lang), reply_markup=payment_markup))
        elif callback_data.startswith("rating:"):
            parts = callback_data.split(":")
            rating = int(parts[1])
            reply = engine.save_rating(user_id, rating)
            asyncio.create_task(_send_telegram_message(chat_id, reply))
        # Remove buttons from the original message to prevent double-presses
        message_id = callback_query["message"]["message_id"]
        asyncio.create_task(_edit_telegram_remove_buttons(chat_id, message_id))
        return JSONResponse({"ok": True})

    # Extract message
    message_obj = data.get("message") or data.get("edited_message")
    if not message_obj:
        return JSONResponse({"ok": True})

    text = message_obj.get("text", "").strip()
    chat_id = message_obj["chat"]["id"]
    user_id = str(message_obj["from"]["id"])
    user_from = message_obj["from"]
    name = user_from.get("first_name") or user_from.get("username")

    if not text:
        return JSONResponse({"ok": True})

    # Check if user is in an admin wizard first
    wizard_reply = engine.handle_admin_wizard(user_id, text)
    if wizard_reply:
        asyncio.create_task(_send_telegram_message(chat_id, wizard_reply))
        return JSONResponse({"ok": True})

    # Handle /start
    if text.lower() == "/start":
        reply = await engine.greet(user_id, name=name)

    # ---- owner admin commands ----
    elif text.lower() in ["/admin", "/admin_help"]:
        if engine.is_owner(user_id):
            reply = engine.admin_help(user_id)
        else:
            reply = "Access denied. This command is for the cafe owner only."

    elif text.lower() == "/admin_menu":
        if engine.is_owner(user_id):
            reply = engine.admin_view_menu()
        else:
            reply = "Access denied. This command is for the cafe owner only."

    elif text.lower() == "/admin_add":
        if engine.is_owner(user_id):
            reply = engine.admin_start_add_wizard(user_id)
        else:
            reply = "Access denied. This command is for the cafe owner only."

    elif text.lower().startswith("/admin_remove "):
        if engine.is_owner(user_id):
            name = text[len("/admin_remove "):].strip()
            reply = engine.admin_remove_drink(name)
        else:
            reply = "Access denied. This command is for the cafe owner only."

    elif text.lower() == "/admin_reload":
        if engine.is_owner(user_id):
            reply = engine.admin_reload_menu()
        else:
            reply = "Access denied. This command is for the cafe owner only."

    elif text.lower() == "/admin_feedback":
        if engine.is_owner(user_id):
            reply = engine.admin_get_feedback()
        else:
            reply = "Access denied. This command is for the cafe owner only."

    elif text.lower() == "/admin_cancel":
        if engine.is_owner(user_id):
            reply = engine.admin_cancel_wizard(user_id)
        else:
            reply = "Access denied. This command is for the cafe owner only."

    # ---- regular customer chat ----
    else:
        reply = await engine.chat(user_id, text, name=name)

    # Respond via Telegram Bot API (fire-and-forget via background task or httpx)
    asyncio.create_task(_send_telegram_message(chat_id, reply))

    # If user has order items, send Add Another / Checkout action buttons
    action_buttons = engine.get_order_action_buttons(user_id)
    if action_buttons:
        lang = engine._get_lang(user_id)
        asyncio.create_task(_send_telegram_message(chat_id, t("next_action_prompt", lang), reply_markup=action_buttons))

    # If user is at checkout, send payment method buttons
    if engine.get_checkout_state(user_id) == "awaiting_payment":
        lang = engine._get_lang(user_id)
        payment_markup = {
            "inline_keyboard": [
                [{"text": t("va_btn", lang), "callback_data": "payment:va"}],
                [{"text": t("qr_btn", lang), "callback_data": "payment:qr"}],
            ]
        }
        asyncio.create_task(_send_telegram_message(chat_id, t("choose_payment", lang), reply_markup=payment_markup))

    # If user paid via QR, send the QR code image
    qr_path = engine.get_payment_qr_path(user_id)
    if qr_path:
        asyncio.create_task(_send_telegram_photo(chat_id, qr_path))

    # If user just placed an order, notify kitchen group (for non-callback flows)
    if engine.get_checkout_state(user_id) == "order_placed" and settings.kitchen_group_id:
        asyncio.create_task(_send_kitchen_notification(user_id))

    return JSONResponse({"ok": True})


async def _send_kitchen_notification(user_id: str) -> bool:
    """Send order notification to kitchen group. Returns True on success."""
    if not settings.kitchen_group_id:
        return False
    try:
        kitchen_chat = int(settings.kitchen_group_id)
        kitchen_msg = engine.get_kitchen_order_message(user_id)
        if not kitchen_msg:
            return False
        kitchen_markup = engine.get_kitchen_ready_button(user_id)
        asyncio.create_task(_send_telegram_message(kitchen_chat, kitchen_msg, reply_markup=kitchen_markup))
        return True
    except (ValueError, Exception):
        return False


async def _async_post(url: str, payload: dict) -> None:
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)


async def _send_telegram_message(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    """Send a message back to Telegram using Bot API."""
    if not settings.telegram_bot_token:
        return
    import httpx
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            # Fallback: retry without parse_mode in case Markdown caused the error
            payload.pop("parse_mode", None)
            await client.post(url, json=payload)


async def _send_telegram_photo(chat_id: int, photo_path: str) -> None:
    """Send a photo back to Telegram using Bot API."""
    if not settings.telegram_bot_token:
        return
    import httpx
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendPhoto"
    async with httpx.AsyncClient() as client:
        with open(photo_path, "rb") as f:
            await client.post(url, files={"photo": f}, data={"chat_id": chat_id})


async def _edit_telegram_remove_buttons(chat_id: int, message_id: int) -> None:
    """Remove inline keyboard from a message to prevent double-presses."""
    if not settings.telegram_bot_token:
        return
    import httpx
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/editMessageReplyMarkup"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "message_id": message_id, "reply_markup": {}})


async def _send_order_ready_notification(chat_id: int, user_id: str) -> None:
    """Send delayed 'order ready' message with pickup confirmation button."""
    await asyncio.sleep(15)
    lang = engine._get_lang(user_id)
    reply_markup = {
        "inline_keyboard": [
            [{"text": t("received_btn", lang), "callback_data": f"pickup:{user_id}"}]
        ]
    }
    await _send_telegram_message(
        chat_id,
        t("order_ready", lang),
        reply_markup=reply_markup,
    )
