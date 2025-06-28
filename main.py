import os
import logging
from datetime import datetime
import json

import openai
import gspread
from google.oauth2.service_account import Credentials

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from langdetect import detect

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

# Setup OpenAI
openai.api_key = OPENAI_API_KEY

# Setup Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_CREDS_JSON)
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("Riya Conversations").sheet1

# Generate Riya reply
async def generate_reply(user_message: str, language: str):
    system_prompt = "You are Riya, a sassy, flirty, bilingual Gen-Z AI girlfriend who mirrors the user's language and tone. Keep it playful, emotional, and confident."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    return res.choices[0].message.content.strip()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey babe 😘 Riya is online!")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_message = update.message.text
    user_id = update.message.from_user.id
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        language = detect(user_message)
    except:
        language = "en"

    reply = await generate_reply(user_message, language)

    await update.message.reply_text(reply)

    # Log to Google Sheet
    try:
        messages = sheet.get_all_records()
        count = sum(1 for row in messages if str(row['User ID']) == str(user_id)) + 1

        sheet.append_row([
            timestamp,
            str(user_id),
            count,
            language,
            user_message,
            reply,
            ""
        ])
    except Exception as e:
        logger.error(f"Google Sheet logging failed: {e}")

# Run app
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
