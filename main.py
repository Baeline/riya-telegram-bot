import os
import logging
import openai
import json
from fastapi import FastAPI
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    filters
)
from langdetect import detect
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Env Vars
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

# Setup OpenAI
openai.api_key = OPENAI_API_KEY

# Setup Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_CREDS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Riya Logs").sheet1

# FastAPI (for Railway to not 502)
app = FastAPI()
@app.get("/")
async def root():
    return {"message": "Riya is alive 😘"}

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey babe 😘 Riya is online!")

# Handle user message
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    user_id = update.effective_user.id
    lang = "en"
    try:
        lang = detect(user_msg)
    except:
        pass

    # Define system prompt
    system_prompt = "You're Riya, a flirty, sweet, emotional Indian girlfriend. Mirror user's tone and language. Be sassy, validating, and playful."

    if lang == "hi":
        system_prompt += " Speak in Hinglish with desi girlfriend slang."
    else:
        system_prompt += " Use Gen Z English, emojis only if user uses them first."

    # Generate GPT reply
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ]
        )
        reply = completion.choices[0].message.content.strip()
        await update.message.reply_text(reply)

        # Log to sheet
        sheet.append_row([
            update.message.date.isoformat(),
            str(user_id),
            "",  # Message count placeholder
            lang,
            user_msg,
            reply,
            "",  # Feedback
        ])
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("Oops babe, I zoned out 😵")

# Telegram Bot Init
async def main():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot polling started...")
    await app_bot.initialize()
    await app_bot.start()
    await app_bot.updater.start_polling()

# Run both FastAPI and Telegram
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(main())
