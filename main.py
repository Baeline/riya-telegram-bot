
import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
import openai
import json
import gspread
from google.oauth2.service_account import Credentials
import razorpay
from fastapi import FastAPI, Request
from telegram.constants import ParseMode

# ENV variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_LINK = "https://rzp.io/rzp/93E7TRqj"

# Setup
app = FastAPI()
openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

# Google Sheets logging setup
creds = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
scopes = ['https://www.googleapis.com/auth/spreadsheets']
credentials = Credentials.from_service_account_info(creds, scopes=scopes)
gc = gspread.authorize(credentials)
sheet = gc.open("Riya Conversations").sheet1

# In-memory user state
user_message_count = {}
verified_users = set()

# Telegram UI
def get_pay_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💖 Unlock More Messages", url=RAZORPAY_LINK)]
    ])

# Razorpay Webhook
@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    payment_status = body.get("event")
    payload = body.get("payload", {})
    email = payload.get("payment", {}).get("entity", {}).get("email", "")
    contact = payload.get("payment", {}).get("entity", {}).get("contact", "")
    if payment_status == "payment.captured":
        verified_users.add(email or contact)
    return {"status": "ok"}

# GPT Reply Generator
async def generate_reply(prompt: str, language: str = "en") -> str:
    system_prompt = (
        "You're Riya, a chaotic, flirty, emotional Indian virtual girlfriend. "
        "Talk in a playful Hinglish tone. Use emojis. Be unpredictable, spicy but sweet."
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message["content"]

# Handle user messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_lang = update.effective_user.language_code or "en"
    user_msg = update.message.text.strip()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Count messages
    count = user_message_count.get(user_id, 0)
    if count >= 5 and user_id not in verified_users:
        await update.message.reply_text(
            "Hey cutie 😘 I’m Riya — Delhi’s sassiest virtual bae."
            "You’ve used your 5 free messages. 💔 Want more spicy fun?",
            reply_markup=get_pay_button()
        )
        return

    # Generate reply
    reply = await generate_reply(user_msg, user_lang)
    await update.message.reply_text(reply, parse_mode=ParseMode.HTML)

    # Log conversation
    sheet.append_row([now, user_id, count + 1, user_lang, user_msg, reply])

    # Update counter
    user_message_count[user_id] = count + 1

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Heyyy 🤍 I’m Riya — your chaotic virtual bae!

Let’s chat, flirt, vibe 😘",
    )

# Telegram bot startup
async def main():
    app_ = ApplicationBuilder().token(BOT_TOKEN).build()
    app_.add_handler(CommandHandler("start", start))
    app_.add_handler(CallbackQueryHandler(lambda *_: None))  # Placeholder
    app_.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app_.run_polling()

# Async start
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.create_task(main())
