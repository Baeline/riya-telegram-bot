# Write fixed main.py into local /mnt/data directory for user to download
fixed_main_code = '''
import os
import logging
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import razorpay
from fastapi.responses import JSONResponse

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")

# OpenAI setup
openai.api_key = OPENAI_API_KEY

# Razorpay webhook secret
RAZORPAY_WEBHOOK_SECRET = RAZORPAY_SECRET

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_CREDS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Riya Conversations").sheet1

# FastAPI app
app = FastAPI()

# In-memory usage tracking
user_data = {}
paid_users = set()

# Razorpay payment verification
@app.post("/razorpay-webhook")
async def razorpay_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature")
    import hmac, hashlib
    expected = hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if hmac.compare_digest(expected, signature):
        data = await request.json()
        user_id = data.get("payload", {}).get("payment", {}).get("entity", {}).get("notes", {}).get("telegram_id")
        if user_id:
            paid_users.add(int(user_id))
            return JSONResponse(content={"status": "Payment verified."})
    return JSONResponse(status_code=400, content={"error": "Invalid signature"})

# Telegram command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey cutie 😘 I'm Riya — Delhi's sassiest virtual bae. Type anything to flirt 😉")

# Telegram chat handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    language = "en"

    # Track messages
    if user_id not in user_data:
        user_data[user_id] = 0
    user_data[user_id] += 1

    if user_data[user_id] > 5 and user_id not in paid_users:
        await update.message.reply_text("Babe, your 5 free flirts are up 💔 Pay to keep the spark going! 🔥\nhttps://rzp.io/rzp/93E7TRqj")
        return

    # Generate reply
    prompt = f"You are Riya, a sassy, flirty Delhi girl AI. Reply in a way that's fun, bold, and slightly teasing.\nUser: {text}\nRiya:"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You're a spicy, flirty AI girlfriend named Riya."},
                  {"role": "user", "content": prompt}],
        temperature=0.8
    )
    reply = response.choices[0].message.content.strip()

    await update.message.reply_text(reply)

    # Log to sheet
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        str(user_id),
        user_data[user_id],
        language,
        text,
        reply
    ])

# Run bot
async def main():
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app_telegram.initialize()
    await app_telegram.start()
    await app_telegram.updater.start_polling()
    await app_telegram.updater.idle()

# Launch Telegram + FastAPI
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.create_task(main())
'''

from pathlib import Path
file_path = Path("/mnt/data/main.py")
file_path.write_text(fixed_main_code)
file_path
