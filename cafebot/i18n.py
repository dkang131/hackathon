"""Language utilities — lightweight detection + translated templates."""

import re

# ISO 639-1 -> friendly language name
_LANG_NAMES: dict[str, str] = {
    "en": "English",
    "id": "Indonesian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "th": "Thai",
    "vi": "Vietnamese",
    "tl": "Tagalog",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "pl": "Polish",
    "nl": "Dutch",
}

# Lightweight keyword/character based detection (no langdetect dependency)
_ID_KEYWORDS = {
    "saya", "aku", "kamu", "dia", "ini", "itu", "yang", "dan", "atau", "dengan",
    "boleh", "mau", "tidak", "nggak", "gak", "iya", "ya",
    "deh", "dong", "aja", "sih", "lah", "kok", "begitu", "sangat", "banget", "sekali",
    "banyak", "sedikit", "bagus", "lelah", "capek", "senang", "sedih", "marah", "sakit",
    "haus", "lapar", "baik", "hari", "kali", "sudah", "sudahlah", "makasih", "terima",
    "kasih", "minum", "makan", "suka", "enak", "pagi", "siang", "malam", "selamat",
    "lagi", "pusing", "ngantuk", "bosan", "takut", "malas", "butuh", "ingin", "kangen",
    "kecewa", "nangis", "ketawa", "pulang", "kerja", "tidur", "bangun", "jalan",
    "datang", "pergi", "lihat", "dengar", "bicara", "pikir", "tahu", "lupa", "ingat",
    "cari", "temukan", "bawa", "beri", "buka", "tutup", "masuk", "keluar", "naik",
    "turun", "cepat", "lambat", "mudah", "sulit",
}

_ES_KEYWORDS = {
    "hola", "amigo", "amiga", "gracias", "por", "favor", "bien", "muy", "mucho",
    "como", "esta", "estoy", "tengo", "quiero", "me", "te", "la", "el", "un", "una",
    "los", "las", "del", "al", "con", "sin", "para", "pero", "que", "cafe",
}


# Single-word Indonesian identifiers — common responses that should be detected even alone
_ID_SINGLE_WORDS = {"boleh", "iya", "ya", "mau", "nggak", "gak", "tidak", "makasih", "terima", "kasih", "baik", "oke", "gas", "setuju"}


def detect_language_simple(text: str) -> str:
    """Fast heuristic language detection. Returns ISO 639-1 code."""
    if not text:
        return "en"
    t = text.lower().strip()
    # Single-word Indonesian catch
    if t in _ID_SINGLE_WORDS:
        return "id"
    # Indonesian keyword check
    words = set(re.findall(r"[a-z]+", t))
    if len(words & _ID_KEYWORDS) >= 2:
        return "id"
    # Spanish keyword check
    if len(words & _ES_KEYWORDS) >= 2:
        return "es"
    # Character-based checks
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", text):
        return "ja"
    if re.search(r"[\uac00-\ud7af]", text):
        return "ko"
    if re.search(r"[áéíóúñü¡¿]", text):
        return "es"
    return "en"


def language_name(code: str) -> str:
    """Get friendly language name for display / logging."""
    return _LANG_NAMES.get(code, _LANG_NAMES.get(code.split("-")[0], "English"))


# ---------- Translated templates for hardcoded bot strings ----------

_TEMPLATES: dict[str, dict[str, str]] = {
    "confirmation": {
        "en": "Yes, great choice! I can already picture you sipping that.",
        "id": "Pilihan yang bagus! Aku sudah bisa membayangkan kamu menikmatinya.",
        "zh": "太棒了！我能想象你品尝它的样子。",
        "ja": "素敵な選択！もう飲んでいる姿が目に浮かぶよ。",
        "ko": "좋은 선택이야! 벌써 마시는 모습이 눈에 선해.",
        "es": "¡Sí, excelente elección! Ya me imagino disfrutándolo.",
    },
    "order_empty": {
        "en": "Your order's empty right now. Let's fix that!",
        "id": "Pesananmu masih kosong nih. Ayo kita pilih sesuatu!",
        "zh": "你的订单还是空的。我们来点些什么吧！",
        "ja": "まだ注文は空っぽだよ。何か選ぼう！",
        "ko": "아직 주문이 비어있어. 뭔가 골라보자!",
        "es": "Tu pedido está vacío. ¡Vamos a arreglar eso!",
    },
    "order_title": {
        "en": "🧾 *Your Order*",
        "id": "🧾 *Pesananmu*",
        "zh": "🧾 *你的订单*",
        "ja": "🧾 *ご注文*",
        "ko": "🧾 *주문 내역*",
        "es": "🧾 *Tu Pedido*",
    },
    "total": {
        "en": "_Total: ${total:.2f}_",
        "id": "_Total: ${total:.2f}_",
        "zh": "_总计: ${total:.2f}_",
        "ja": "_合計: ${total:.2f}_",
        "ko": "_총액: ${total:.2f}_",
        "es": "_Total: ${total:.2f}_",
    },
    "menu_title": {
        "en": "☕ *Our Menu*",
        "id": "☕ *Menu Kami*",
        "zh": "☕ *菜单*",
        "ja": "☕ *メニュー*",
        "ko": "☕ *메뉴*",
        "es": "☕ *Nuestro Menú*",
    },
    "add_another": {
        "en": "☕ Add Another Drink",
        "id": "☕ Tambah Minuman",
        "zh": "☕ 再加一杯",
        "ja": "☕ もう一杯追加",
        "ko": "☕ 음료 추가",
        "es": "☕ Agregar Otra Bebida",
    },
    "checkout_btn": {
        "en": "💳 Checkout",
        "id": "💳 Bayar",
        "zh": "💳 结账",
        "ja": "💳 会計",
        "ko": "💳 결제",
        "es": "💳 Pagar",
    },
    "next_action_prompt": {
        "en": "What would you like to do next?",
        "id": "Mau ngapain selanjutnya?",
        "zh": "接下来想做什么？",
        "ja": "次は何をしますか？",
        "ko": "다음으로 뭘 할까?",
        "es": "¿Qué te gustaría hacer ahora?",
    },
    "choose_payment": {
        "en": "Choose your payment method:",
        "id": "Pilih metode pembayaran:",
        "zh": "请选择支付方式：",
        "ja": "支払い方法を選んでください：",
        "ko": "결제 방법을 선택해줘:",
        "es": "Elige tu método de pago:",
    },
    "va_btn": {
        "en": "🏦 Virtual Account",
        "id": "🏦 Virtual Account",
        "zh": "🏦 虚拟账户",
        "ja": "🏦 振込",
        "ko": "🏦 가상계좌",
        "es": "🏦 Cuenta Virtual",
    },
    "qr_btn": {
        "en": "📱 QR Code",
        "id": "📱 Kode QR",
        "zh": "📱 二维码",
        "ja": "📱 QRコード",
        "ko": "📱 QR 코드",
        "es": "📱 Código QR",
    },
    "pay_va": {
        "en": "Please transfer to this Virtual Account:\n  `{va}`\n\nTap *I've Paid* once you're done!",
        "id": "Silakan transfer ke Virtual Account ini:\n  `{va}`\n\nTap *Sudah Bayar* setelah selesai!",
        "zh": "请转账至以下虚拟账户：\n  `{va}`\n\n完成后点击 *已付款*！",
        "ja": "この口座に振り込んでください：\n  `{va}`\n\n完了したら *支払い完了* をタップ！",
        "ko": "이 가상계좌로 입금해줘:\n  `{va}`\n\n완료되면 *결제 완료* 눌러줘!",
        "es": "Por favor transfiere a esta cuenta virtual:\n  `{va}`\n\n¡Toca *Ya Pagué* cuando termines!",
    },
    "pay_qr": {
        "en": "Please scan the QR code below to pay. Tap *I've Scanned* once you're done!",
        "id": "Silakan scan kode QR di bawah untuk bayar. Tap *Sudah Scan* setelah selesai!",
        "zh": "请扫描下方二维码付款。完成后点击 *已扫描*！",
        "ja": "下のQRコードを読み取って支払ってください。完了したら *スキャン完了* をタップ！",
        "ko": "아래 QR 코드를 스캔해서 결제해줘. 완료되면 *스캔 완료* 눌러줘!",
        "es": "Escanea el código QR para pagar. ¡Toca *Ya Escaneé* cuando termines!",
    },
    "paid_va": {
        "en": "✅ I've Paid",
        "id": "✅ Sudah Bayar",
        "zh": "✅ 已付款",
        "ja": "✅ 支払い完了",
        "ko": "✅ 결제 완료",
        "es": "✅ Ya Pagué",
    },
    "paid_qr": {
        "en": "✅ I've Scanned",
        "id": "✅ Sudah Scan",
        "zh": "✅ 已扫描",
        "ja": "✅ スキャン完了",
        "ko": "✅ 스캔 완료",
        "es": "✅ Ya Escaneé",
    },
    "payment_received": {
        "en": "Your payment has been received! We'll notify you when your order is ready for pickup.",
        "id": "Pembayaranmu sudah diterima! Kami akan kabari kalau pesananmu sudah siap diambil.",
        "zh": "付款已收到！订单准备好取餐时我们会通知你。",
        "ja": "お支払いを確認しました！注文が準備でき次第お知らせします。",
        "ko": "결제가 확인되었어! 주문이 준비되면 알려줄게.",
        "es": "¡Tu pago ha sido recibido! Te avisaremos cuando tu pedido esté listo.",
    },
    "order_ready": {
        "en": "Great news! Your order is ready for pickup. Please confirm once you've received it!",
        "id": "Kabar baik! Pesananmu sudah siap diambil. Konfirmasi ya kalau sudah diterima!",
        "zh": "好消息！你的订单可以取餐了。收到后请确认！",
        "ja": "良いお知らせです！注文が受け取り可能になりました。受け取ったら確認してください！",
        "ko": "좋은 소식이야! 주문이 픽업 준비가 되었어. 받으면 확인해줘!",
        "es": "¡Buenas noticias! Tu pedido está listo para recoger. ¡Confirma cuando lo tengas!",
    },
    "received_btn": {
        "en": "✅ Received",
        "id": "✅ Sudah Diterima",
        "zh": "✅ 已收到",
        "ja": "✅ 受け取り完了",
        "ko": "✅ 수령 완료",
        "es": "✅ Recibido",
    },
    "enjoy": {
        "en": "Enjoy your drinks! Thanks for visiting CafeMate. Come back soon!",
        "id": "Selamat menikmati! Terima kasih sudah mampir ke CafeMate. Sampai jumpa lagi!",
        "zh": "请享用！感谢光临CafeMate。欢迎再来！",
        "ja": "お楽しみください！CafeMateをご利用いただきありがとう。また来てね！",
        "ko": "맛있게 마셔! CafeMate를 이용해줘서 고마워. 다음에 또 와!",
        "es": "¡Disfruta! Gracias por visitar CafeMate. ¡Vuelve pronto!",
    },
    "feedback_prompt": {
        "en": "How was your experience? Please rate us:",
        "id": "Gimana pengalamanmu? Kasih rating ya:",
        "zh": "体验如何？请给我们评分：",
        "ja": "体験はいかがでしたか？評価をお願いします：",
        "ko": "경험이 어땠어? 별점을 남겨줘:",
        "es": "¿Cómo fue tu experiencia? Por favor califícanos:",
    },
    "rate_comment": {
        "en": "Feel free to share any comments about your experience, or just say *done* to finish.",
        "id": "Boleh kasih komentar tentang pengalamanmu, atau ketik *selesai* untuk selesai.",
        "zh": "欢迎分享你的体验感受，或输入 *完成* 结束。",
        "ja": "体験についてコメントがあればどうぞ。終了する場合は *完了* と入力してください。",
        "ko": "경험에 대한 코멘트를 남겨도 돼. 끝내려면 *완료* 라고 말해줘.",
        "es": "Siéntete libre de compartir comentarios, o escribe *listo* para terminar.",
    },
    "thanks_feedback": {
        "en": "Thank you for your feedback! We appreciate you taking the time to share your experience. See you next time!",
        "id": "Terima kasih atas feedbacknya! Kami menghargai waktumu. Sampai jumpa lagi!",
        "zh": "感谢你的反馈！我们很重视你的体验分享。下次见！",
        "ja": "フィードバックありがとう！あなたの体験を共有してくれて嬉しいです。またね！",
        "ko": "피드백 고마워! 시간 내서 경험을 공유해줘서 고마워. 다음에 또 봐!",
        "es": "¡Gracias por tu feedback! Apreciamos que compartas tu experiencia. ¡Hasta la próxima!",
    },
    "no_order": {
        "en": "You haven't ordered anything yet! Let's pick something out first.",
        "id": "Kamu belum pesan apa-apa nih! Ayo pilih sesuatu dulu.",
        "zh": "你还没点任何东西！我们先选一些吧。",
        "ja": "まだ何も注文してないよ！まず何か選ぼう。",
        "ko": "아직 아무것도 주문하지 않았어! 먼저 뭔가 골라보자.",
        "es": "¡Aún no has pedido nada! Vamos a elegir algo primero.",
    },
    "removed": {
        "en": "Removed {name} from your order.",
        "id": "{name} sudah dihapus dari pesananmu.",
        "zh": "已将{name}从订单中移除。",
        "ja": "{name}を注文から削除しました。",
        "ko": "{name}을(를) 주문에서 제거했어.",
        "es": "Eliminado {name} de tu pedido.",
    },
    "not_in_order": {
        "en": "{name} isn't in your order.",
        "id": "{name} tidak ada di pesananmu.",
        "zh": "你的订单中没有{name}。",
        "ja": "{name}は注文に入っていません。",
        "ko": "주문에 {name}이(가) 없어.",
        "es": "{name} no está en tu pedido.",
    },
    "scan_qr_prompt": {
        "en": "Tap the button after you scan the QR code:",
        "id": "Tap tombol setelah scan kode QR:",
        "zh": "扫描二维码后点击按钮：",
        "ja": "QRコードを読み取ったらボタンをタップ：",
        "ko": "QR 코드를 스캔한 후 버튼을 눌러줘:",
        "es": "Toca el botón después de escanear el QR:",
    },
    "transfer_prompt": {
        "en": "Tap the button after you complete the transfer:",
        "id": "Tap tombol setelah transfer selesai:",
        "zh": "完成转账后点击按钮：",
        "ja": "振り込みが完了したらボタンをタップ：",
        "ko": "입금이 완료되면 버튼을 눌러줘:",
        "es": "Toca el botón después de completar la transferencia:",
    },
    "add_prompt": {
        "en": "What would you like to add?",
        "id": "Mau tambah apa?",
        "zh": "想加点什么？",
        "ja": "何を追加しますか？",
        "ko": "뭘 추가할까?",
        "es": "¿Qué te gustaría agregar?",
    },
    "session_timeout": {
        "en": "Your session has timed out after 60 seconds of inactivity. Please type /start to begin again.",
        "id": "Sesi kamu telah berakhir setelah 60 detik tidak aktif. Ketik /start untuk memulai lagi.",
        "zh": "您的会话因60秒无操作已超时。请输入 /start 重新开始。",
        "ja": "60秒間操作がなかったため、セッションがタイムアウトしました。もう一度 /start と入力してください。",
        "ko": "60초 동안 활동이 없어 세션이 만료되었어. 다시 /start 를 입력해줘.",
        "es": "Tu sesión ha expirado tras 60 segundos de inactividad. Escribe /start para comenzar de nuevo.",
    },
}


def t(key: str, lang: str = "en", **kwargs) -> str:
    """Get translated template string. Falls back to English if translation missing."""
    texts = _TEMPLATES.get(key, {})
    text = texts.get(lang, texts.get("en", key))
    if kwargs:
        return text.format(**kwargs)
    return text


# Short aliases for convenience
CONFIRMATION = "confirmation"
ORDER_EMPTY = "order_empty"
ORDER_TITLE = "order_title"
TOTAL = "total"
MENU_TITLE = "menu_title"
ADD_ANOTHER = "add_another"
CHECKOUT_BTN = "checkout_btn"
NEXT_ACTION = "next_action_prompt"
CHOOSE_PAYMENT = "choose_payment"
VA_BTN = "va_btn"
QR_BTN = "qr_btn"
PAY_VA = "pay_va"
PAY_QR = "pay_qr"
PAID_VA = "paid_va"
PAID_QR = "paid_qr"
PAYMENT_RECEIVED = "payment_received"
ORDER_READY = "order_ready"
RECEIVED_BTN = "received_btn"
ENJOY = "enjoy"
FEEDBACK_PROMPT = "feedback_prompt"
RATE_COMMENT = "rate_comment"
THANKS_FEEDBACK = "thanks_feedback"
NO_ORDER = "no_order"