import os
import logging
import openai
import gspread
from datetime import datetime
from langdetect import detect
from fastapi import FastAPI
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from google.oauth2.service_account import Credentials

# ENV variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI config
openai.api_key = OPENAI_API_KEY

# FastAPI dummy app (needed by Railway)
app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Riya is slaying"}

# Authenticate with Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(eval(GOOGLE_CREDS_JSON), scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("Riya Conversations").sheet1  # Sheet name must match

# Generate response from OpenAI
async def generate_reply(prompt, lang):
    system_prompt = "You're Riya — a flirty, sassy, emotional virtual girlfriend who mirrors the user's mood."

    if lang == "hi":
        system_prompt += " Speak in Hinglish with desi tone and light roasts."
    elif lang == "en":
        system_prompt += " Speak in Gen Z English with emojis and banter."
    else:
        system_prompt += " Be friendly and curious. Use light emoji."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content']

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hey babe 😘 Riya is online!")

# Main message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.effective_user.id
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        lang = detect(user_message)
    except:
        lang = "unknown"

    try:
        reply = await generate_reply(user_message, lang)
    except Exception as e:
        reply = "Oops babe, I zoned out 😵"
        logger.error(f"OpenAI error: {e}")

    # Send reply
    await context.bot.send_message(chat_id=update.effective_chat.id, text=reply)

    # Log to Google Sheet
    try:
        sheet.append_row([timestamp, user_id, user_message, lang, reply])
    except Exception as e:
        logger.error(f"GSheet logging failed: {e}")

# Telegram app setup
def run_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Riya is live and logging 👑")
    application.run_polling()

# Entry point
if __name__ == "__main__":
    run_bot()
