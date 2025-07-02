
import os, json, logging, hmac, hashlib, requests
from fastapi import FastAPI, Request
from langdetect import detect
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ────────────────────────────────────────────────────────────────
# ▶︎ ENVIRONMENT
# ────────────────────────────────────────────────────────────────
BOT_TOKEN                = os.getenv("BOT_TOKEN")
OPENAI_API_KEY           = os.getenv("OPENAI_API_KEY")
RAZORPAY_KEY_ID          = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET      = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET  = os.getenv("RAZORPAY_WEBHOOK_SECRET")
GOOGLE_CREDS_JSON        = os.getenv("GOOGLE_CREDS_JSON")
FREE_LIMIT               = int(os.getenv("FREE_LIMIT", 5))
PORT                     = int(os.getenv("PORT", 8000))

openai.api_key = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)

# ────────────────────────────────────────────────────────────────
# ▶︎ GLOBAL STATE
# ────────────────────────────────────────────────────────────────
user_sessions: dict[int, dict] = {}
paid_users:    set[int]        = set()

# ────────────────────────────────────────────────────────────────
# ▶︎ GOOGLE SHEET – conversation logging
# ────────────────────────────────────────────────────────────────
scope   = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds   = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS_JSON), scope)
client  = gspread.authorize(creds)
sheet   = client.open("Riya Conversations").sheet1

def log_to_sheet(user_id: int, user_msg: str, reply: str) -> None:
    try:
        sheet.append_row([str(user_id), user_msg, reply])
    except Exception as exc:
        logging.error(f"Google‑sheet log failed: {exc}")

# ────────────────────────────────────────────────────────────────
# ▶︎ RAZORPAY HELPERS
# ────────────────────────────────────────────────────────────────
ORDER_AMOUNT_PAISA = 49 * 100  # ₹49 → paisa

def create_order(user_id: int) -> dict:
    """Create Razorpay order and return the json response."""
    rsp = requests.post(
        "https://api.razorpay.com/v1/orders",
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
        json={
            "amount"         : ORDER_AMOUNT_PAISA,
            "currency"       : "INR",
            "receipt"        : f"tg_{user_id}",
            "payment_capture": 1,
        },
        timeout=10,
    )
    rsp.raise_for_status()
    return rsp.json()

# ────────────────────────────────────────────────────────────────
# ▶︎ OPENAI – generate Riya reply
# ────────────────────────────────────────────────────────────────
async def generate_reply(message: str, lang: str) -> str:
    system_prompt = (
        "You're Riya, the spicy AI girlfriend. Respond with sass & sweetness."  # base
        + (" Speak in Hinglish with desi swag 💕" if lang == "hi" else " Use Gen‑Z flirt 😘")
    )
    rsp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": message},
        ],
    )
    return rsp.choices[0].message.content.strip()

# ────────────────────────────────────────────────────────────────
# ▶︎ TELEGRAM BOT SETUP (handlers only)
# ────────────────────────────────────────────────────────────────
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Heyy I'm Riya 💋\nType anything & let's vibe!")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions.setdefault(user_id, {"count": 0})

    # rate‑limit vs paid
    if user_id not in paid_users and user_sessions[user_id]["count"] >= FREE_LIMIT:
        await prompt_payment(update)
        return
    user_sessions[user_id]["count"] += 1

    txt  = update.message.text
    lang = detect(txt)
    reply = await generate_reply(txt, lang)
    await update.message.reply_text(reply)
    log_to_sheet(user_id, txt, reply)

async def on_callback(update: Update, _: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "verify_payment":
        await q.edit_message_text("🔄 Auto‑unlock is running! Payment will unlock chat within seconds ✨")

telegram_app.add_handlers([
    CommandHandler("start", cmd_start),
    CallbackQueryHandler(on_callback),
    MessageHandler(filters.TEXT & ~filters.COMMAND, on_message),
])

# ────────────────────────────────────────────────────────────────
# ▶︎ FASTAPI APP (Telegram & Razorpay webhooks)
# ────────────────────────────────────────────────────────────────
app = FastAPI()

@app.post("/telegram")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, telegram_app.bot)

    if not telegram_app._initialized:
        await telegram_app.initialize()

    await telegram_app.process_update(update)
    return {"ok": True}


@app.post("/razorpay/webhook")
async def razorpay_webhook(req: Request):
    body      = await req.body()
    signature = req.headers.get("X-Razorpay-Signature", "")
    digest    = hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(), msg=body, digestmod=hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, signature):
        return {"status": "invalid signature"}

    payload = json.loads(body)
    if payload.get("event") == "payment.captured":
        receipt = payload["payload"]["payment"]["entity"].get("receipt", "")
        if receipt.startswith("tg_"):
            paid_users.add(int(receipt.split("_", 1)[1]))
            logging.info("✔️  Auto‑unlocked user %s", receipt)
            return {"status": "unlocked"}
    return {"status": "ignored"}

# ────────────────────────────────────────────────────────────────
# ▶︎ PAYMENT PROMPT (Razorpay order link)
# ────────────────────────────────────────────────────────────────
async def prompt_payment(update: Update):
    user_id = update.effective_user.id
    order   = create_order(user_id)
    pay_url = f"https://rzp.io/i/{order['id']}"
    kb      = [[InlineKeyboardButton("💸 Unlock Full Access – ₹49", url=pay_url)]]
    await update.message.reply_text(
        "You’ve used your 5 free messages 💔\n\nWant more? 😉",
        reply_markup=InlineKeyboardMarkup(kb),
    )

# ────────────────────────────────────────────────────────────────
# ▶︎ RUN via uvicorn (Railway start command)
# ────────────────────────────────────────────────────────────────
# Start the bot inside a background thread *once* FastAPI is live.

def _start_bot():
    telegram_app.run_async()  # PTB v20 async‑loop safe

Thread(target=_start_bot, daemon=True).start()

# Nothing else here. Railway launches with:
# uvicorn main:app --host 0.0.0.0 --port ${PORT}

