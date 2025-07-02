import os, logging, json, requests, hmac, hashlib
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from langdetect import detect
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from threading import Thread
import uvicorn

# ENV VARS
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
FREE_LIMIT = int(os.getenv("FREE_LIMIT", 5))

openai.api_key = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)
user_sessions = {}
paid_users = set()

# ✅ FastAPI App
app = FastAPI()

# ✅ Google Sheets Auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS_JSON), scope)
client = gspread.authorize(creds)
sheet = client.open("Riya Conversations").sheet1

def log_to_sheet(user_id, user_message, reply):
    try:
        sheet.append_row([str(user_id), user_message, reply])
    except Exception as e:
        logging.error(f"Sheet log failed: {e}")

# ✅ Razorpay Order Creation
def create_order(user_id):
    url = "https://api.razorpay.com/v1/orders"
    data = {
        "amount": 4900,
        "currency": "INR",
        "receipt": f"tg_{user_id}",
        "payment_capture": 1
    }
    response = requests.post(
        url,
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
        json=data
    )
    return response.json()

# ✅ Razorpay Webhook Endpoint
@app.post("/razorpay/webhook")
async def razorpay_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    expected = hmac.new(
        bytes(RAZORPAY_WEBHOOK_SECRET, 'utf-8'),
        msg=body,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return {"status": "invalid signature"}

    payload = json.loads(body)
    try:
        if payload.get("event") == "payment.captured":
            receipt = payload["payload"]["payment"]["entity"].get("receipt", "")
            if "tg_" in receipt:
                user_id = int(receipt.split("_")[1])
                paid_users.add(user_id)
                logging.info(f"✅ Payment auto-unlocked for user: {user_id}")
                return {"status": "unlocked"}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
    return {"status": "ignored"}

# ✅ OpenAI Response
async def generate_reply(message, language):
    system_prompt = "You're Riya, a flirty, emotional AI girlfriend. Respond with sass and sweetness."
    if language == "hi":
        system_prompt += " Speak in Hinglish with desi swag and emojis 💕"
    else:
        system_prompt += " Use Gen Z tone, flirt, tease, and keep it spicy 😘"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
    )
    return response.choices[0].message.content.strip()

# ✅ Payment Prompt
async def send_payment_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    order = create_order(user_id)
    order_id = order.get("id")
    payment_url = f"https://rzp.io/i/{order_id}" if order_id else "https://rzp.io/l/fallback"

    keyboard = [
        [InlineKeyboardButton("💸 Unlock Full Access – ₹49", url=payment_url)],
        [InlineKeyboardButton("✅ I already paid", callback_data="verify_payment")]
    ]
    await update.message.reply_text(
        "You’ve used up your 5 free messages 💔\n\nWanna keep chatting with me? 😉",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ✅ Telegram Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Heyy, I'm Riya 💋\nType anything to start chatting!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions.setdefault(user_id, {"count": 0})

    if user_id in paid_users:
        pass
    elif user_sessions[user_id]["count"] >= FREE_LIMIT:
        await send_payment_prompt(update, context)
        return
    else:
        user_sessions[user_id]["count"] += 1

    user_message = update.message.text
    language = detect(user_message)
    reply = await generate_reply(user_message, language)
    await update.message.reply_text(reply)
    log_to_sheet(user_id, user_message, reply)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "verify_payment":
        await query.edit_message_text("🔄 We’ve switched to auto-unlock via payment confirmation 💸\nPlease wait a few seconds after you pay ✨")

# ✅ Launch both Telegram Webhook + FastAPI
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(callback_handler))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def set_webhook():
    await telegram_app.bot.set_webhook("https://riya-telegram-bot-production.up.railway.app/telegram")

telegram_app.initialize()
telegram_app.post_init = set_webhook

Thread(target=telegram_app.run_webhook, kwargs={
    "listen": "0.0.0.0",
    "port": int(os.getenv("PORT", 8000)),
    "webhook_path": "/telegram"
}).start()

# ✅ Register Bot Handlers
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(callback_handler))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ✅ Expose Telegram Webhook
@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"status": "ok"}

# ✅ Start Uvicorn server
# ✅ Register Bot Handlers
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(callback_handler))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ✅ Expose Telegram Webhook
@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"status": "ok"}

# ✅ Start Uvicorn server
# ✅ Register Bot Handlers
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(callback_handler))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ✅ Expose Telegram Webhook
@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"status": "ok"}





