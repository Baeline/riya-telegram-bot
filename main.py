import os
import logging
import asyncio
from fastapi import FastAPI
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from langdetect import detect, LangDetectException
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ENV
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

# FastAPI app (required for Railway)
app = FastAPI()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI setup
openai.api_key = OPENAI_API_KEY

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
import json
from oauth2client.service_account import ServiceAccountCredentials

creds_dict = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)
sheet = client.open("Riya Logs").sheet1

# GPT Response Generator
def generate_reply(user_input, lang_code):
    system_prompt = "You're Riya, a flirty bilingual girlfriend. Match the user's vibe."

    if lang_code == "hi":
        system_prompt += " Reply in Hinglish with desi flavor."
    else:
        system_prompt += " Reply in Gen Z English with sass."

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )
    return completion.choices[0].message.content.strip()

# /start Handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey babe 😘 Riya is online!")

# Message Handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name

    # Detect Language Safely
    try:
        lang = detect(user_msg)
    except LangDetectException:
        lang = "unknown"

    # Generate reply
    try:
        reply = generate_reply(user_msg, lang)
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        await update.message.reply_text("Oops babe, I zoned out 😵")

    # Log to Sheet
    try:
        sheet.append_row([
            str(datetime.now()), str(user_id), username, user_msg, lang
        ])
    except Exception as e:
        logger.warning(f"Sheet logging failed: {e}")

# Main Function
async def telegram_main():
    app_builder = ApplicationBuilder().token(BOT_TOKEN).build()
    app_builder.add_handler(CommandHandler("start", start))
    app_builder.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app_builder.initialize()
    await app_builder.start()
    logger.info("✅ Riya is live and logging!")
    await app_builder.updater.start_polling()
    await app_builder.updater.idle()

# Run Telegram Bot in Background
@app.on_event("startup")
async def start_bot():
    asyncio.create_task(telegram_main())
