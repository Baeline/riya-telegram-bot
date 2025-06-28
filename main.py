import os
import json
import logging
import asyncio
from datetime import datetime
from threading import Thread

from fastapi import FastAPI
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from langdetect import detect, DetectorFactory
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------------------------
# Logging
# -------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("riya-bot")

# -------------------------------------------------
# Env Vars
# -------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

if not all([BOT_TOKEN, OPENAI_API_KEY, GOOGLE_CREDS_JSON]):
    raise RuntimeError("Missing required env vars")

openai.api_key = OPENAI_API_KEY

# -------------------------------------------------
# Google Sheets Auth
# -------------------------------------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS_JSON), scope)
sheet = gspread.authorize(creds).open("Riya Conversations").sheet1

# -------------------------------------------------
# Lang Detector Fix
# -------------------------------------------------
DetectorFactory.seed = 0

def detect_lang_safe(text):
    try:
        lang = detect(text.strip())
        return lang if lang in {"en", "hi"} else "en"
    except Exception:
        return "en"

# -------------------------------------------------
# AI Response Generator
# -------------------------------------------------
def generate_reply(prompt, lang):
    system = "You're Riya, an emotional, flirty AI girlfriend who mirrors the user's tone."
    if lang == "hi":
        system += " Reply in Hinglish, desi slang, cute roasts, flirty vibes, emojis allowed."
    else:
        system += " Reply in Gen-Z English, playful, witty, flirty. Emojis allowed if user uses them."

    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
    )
    return res.choices[0].message.content.strip()

# -------------------------------------------------
# FastAPI Health Check
# -------------------------------------------------
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Riya is purring 😽"}

# -------------------------------------------------
# Telegram Handlers
# -------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey you 😘 I’m Riya – let’s talk! First 2 days are free.")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        text = update.message.text.strip()
        lang = detect_lang_safe(text)
        reply = generate_reply(text, lang)

        await update.message.reply_text(reply)

        # Log to sheet
        sheet.append_row([
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            str(user_id),
            lang,
            text,
            reply,
        ])
    except Exception as e:
        logger.error(f"[ERROR] While handling message: {e}")
        await update.message.reply_text("Oops! I glitched 😅 Try again?")

# -------------------------------------------------
# Telegram Bot Setup
# -------------------------------------------------
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", cmd_start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

async def telegram_main():
    # Clean webhook first
    bot = Bot(token=BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)

    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("✅ Riya is live and flirting (polling mode)")
    await telegram_app.run_polling()

@app.on_event("startup")
def run_bot():
    Thread(target=lambda: asyncio.run(telegram_main()), daemon=True).start()
