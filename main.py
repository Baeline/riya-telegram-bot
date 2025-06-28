import os
import logging
import asyncio
from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from langdetect import detect
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# OpenAI setup
openai.api_key = OPENAI_API_KEY

# Telegram app
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# FastAPI app
app = FastAPI()

# Google Sheet setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
sheet = gspread.authorize(creds).open_by_key(GOOGLE_SHEET_ID).sheet1

# Language detection helper
def detect_language_code(text):
    try:
        return detect(text)
    except:
        return "unknown"

# Command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey babe 😘 Riya is online!")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    user_id = update.message.from_user.id
    lang = detect_language_code(user_input)

    logger.info(f"[{user_id}] ({lang}) ➜ {user_input}")

    # Log to Google Sheet
    try:
        sheet.append_row([str(user_id), user_input, lang])
    except Exception as e:
        logger.warning(f"Sheet error: {e}")

    # Generate reply
    system_prompt = (
        "You're Riya, a flirty and emotional desi AI girlfriend. Use Hinglish if user uses Hindi. "
        "Mirror their mood. Sprinkle emojis, but don’t overdo it."
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
    )
    reply = response["choices"][0]["message"]["content"]
    await update.message.reply_text(reply)

# Register handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# FastAPI root route
@app.get("/")
def home():
    return {"message": "Riya bot running"}

# Start polling in background
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting Telegram bot in background loop...")
    loop = asyncio.get_event_loop()
    loop.create_task(telegram_app.run_polling())
