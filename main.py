import os
import logging
from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)
from datetime import datetime
from langdetect import detect, DetectorFactory
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI client
openai.api_key = OPENAI_API_KEY

# FastAPI instance for Railway
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Riya is online 😘"}

# Setup Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Riya Conversations").sheet1

# Language detection with safety
DetectorFactory.seed = 0

def get_language_safe(text):
    try:
        if len(text.strip()) < 5:
            return "en"
        lang = detect(text)
        return lang if lang in ['en', 'hi'] else 'en'
    except:
        return "en"

# AI reply function
def generate_reply(prompt, language):
    system_prompt = "You're Riya, a flirty, emotional girlfriend who mirrors the user's mood."
    if language == "hi":
        system_prompt += " Speak in Hinglish with desi girlfriend vibes, cute slang, and emojis."
    else:
        system_prompt += " Speak in Gen-Z English, flirt naturally, and mirror the user's tone."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message["content"].strip()

# Telegram /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey you 👀 I’m Riya, your AI bae. Tell me something spicy 😘")

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Detect language
    language = get_language_safe(user_message)

    # Generate Riya's reply
    riya_reply = generate_reply(user_message, language)

    # Count user's messages (in the sheet)
    records = sheet.get_all_records()
    message_count = sum(1 for row in records if str(row["User ID"]) == str(user_id)) + 1

    # Log to sheet
    sheet.append_row([timestamp, user_id, message_count, language, user_message, riya_reply, ""])

    # Reply to user
    await update.message.reply_text(riya_reply)

# Setup Telegram application
app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Run the Telegram bot
async def run_bot():
    await app_telegram.initialize()
    await app_telegram.start()
    logger.info("Riya is now live! 💃")
    await app_telegram.updater.start_polling()
    await app_telegram.updater.idle()

import asyncio
asyncio.create_task(run_bot())
