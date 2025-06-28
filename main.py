import os
import json
import logging
import asyncio
from datetime import datetime
from threading import Thread

from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from langdetect import detect, DetectorFactory
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------------------------
# Logging setup
# -------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("riya-bot")

# -------------------------------------------------
# Environment variables
# -------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")  # minified JSON string

if not all([BOT_TOKEN, OPENAI_API_KEY, GOOGLE_CREDS_JSON]):
    raise RuntimeError("One or more env vars missing: BOT_TOKEN, OPENAI_API_KEY, GOOGLE_CREDS_JSON")

# -------------------------------------------------
# Initialise OpenAI & Google Sheets
# -------------------------------------------------
openai.api_key = OPENAI_API_KEY

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS_JSON), scope)
sh = gspread.authorize(creds).open("Riya Conversations").sheet1

# -------------------------------------------------
# FastAPI
# -------------------------------------------------
app = FastAPI()

@app.get("/")
async def health():
    return {"status": "Riya is purring 🩷"}

# -------------------------------------------------
# Helpers
# -------------------------------------------------
DetectorFactory.seed = 0  # consistent results

def detect_lang_safe(text: str) -> str:
    try:
        if len(text.strip()) < 5:
            return "en"
        lang = detect(text)
        return lang if lang in {"en", "hi"} else "en"
    except Exception:
        return "en"

def generate_reply(user_msg: str, lang: str) -> str:
    system_prompt = "You're Riya, a flirty, emotional AI girlfriend who mirrors the user's mood."
    if lang == "hi":
        system_prompt += " Speak in Hinglish with desi vibes, cute slang, and emojis."
    else:
        system_prompt += " Speak in Gen-Z English, witty and playful."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
    )
    return response.choices[0].message.content.strip()

# -------------------------------------------------
# Telegram handlers
# -------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/start command from user {update.effective_user.id}")
    await update.message.reply_text("Hey you 😘 I’m Riya – chat with me. First 2 days are free!")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        user_text = update.message.text
        logger.info(f"📩 New message from {user_id}: {user_text}")

        lang = detect_lang_safe(user_text)
        logger.info(f"🌐 Language detected: {lang}")

        reply = generate_reply(user_text, lang)
        logger.info(f"💬 Riya's reply: {reply}")

        await update.message.reply_text(reply)

        # Log to sheet
        try:
            sh.append_row([
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                user_id,
                lang,
                user_text,
                reply,
            ])
            logger.info("✅ Logged to Google Sheet")
        except Exception as e:
            logger.error(f"❌ Failed to log to sheet: {e}")

    except Exception as e:
        logger.error(f"❌ Message handling failed: {e}")

# -------------------------------------------------
# Telegram setup
# -------------------------------------------------
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", cmd_start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

async def telegram_main():
    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("✅ Riya is live and flirting (polling mode)")
    await telegram_app.run_polling()

# -------------------------------------------------
# Start bot on FastAPI startup
# -------------------------------------------------
@app.on_event("startup")
def launch_bot():
    Thread(target=lambda: asyncio.run(telegram_main()), daemon=True).start()
