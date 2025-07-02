
import os
import json
import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import hmac
import hashlib

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")
GOOGLE_CREDS_JSON = json.loads(os.getenv("GOOGLE_CREDS_JSON"))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup OpenAI
openai.api_key = OPENAI_API_KEY

# Setup Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDS_JSON, scope)
client = gspread.authorize(creds)
sheet = client.open("Riya Conversations").sheet1

# Memory store
user_messages = {}
paid_users = set()

# Razorpay payment link
PAYMENT_LINK = "https://rzp.io/rzp/93E7TRqj"

# Typing helper
async def send_typing(context, chat_id):
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

# Generate flirty replies
def generate_reply(user_message, language="en"):
    system_prompt = (
        "You’re Riya, a sassy, emotional virtual girlfriend from Delhi. "
        "You flirt, tease, and sometimes roast. Keep it spicy and desi. Respond only as her."
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    return response['choices'][0]['message']['content'].strip()

# Save to Google Sheet
def log_conversation(user_id, msg_count, lang, user_msg, riya_reply):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([now, user_id, msg_count, lang, user_msg, riya_reply])

# Start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey cutie 😘 I'm Riya – Delhi's sassiest virtual bae.Say hi and let's flirt 💋")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    user_messages.setdefault(user_id, []).append(user_message)

    if user_id not in paid_users and len(user_messages[user_id]) > 5:
        button = InlineKeyboardMarkup([[InlineKeyboardButton("Unlock 🔓", url=PAYMENT_LINK)]])
        await update.message.reply_text("Your free messages are over 💔 Tap below to continue chatting with me 💋", reply_markup=button)
        return

    await send_typing(context, update.effective_chat.id)
    reply = generate_reply(user_message)
    await update.message.reply_text(reply)

    log_conversation(user_id, len(user_messages[user_id]), "en", user_message, reply)

# Webhook setup
app = FastAPI()

@app.post("/webhook")
async def webhook_handler(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    computed = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()

    if hmac.compare_digest(computed, signature):
        data = await request.json()
        if data.get("event") == "payment.captured":
            user_id = str(data["payload"]["payment"]["entity"].get("notes", {}).get("user_id"))
            if user_id:
                paid_users.add(int(user_id))
        return {"status": "ok"}
    return {"status": "unauthorized"}

# Launch Telegram bot
async def main():
    app_ = ApplicationBuilder().token(BOT_TOKEN).build()
    app_.add_handler(CommandHandler("start", start))
    app_.add_handler(CallbackQueryHandler(lambda *_: None))  # placeholder
    app_.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app_.run_polling()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
