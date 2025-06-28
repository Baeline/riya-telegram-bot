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
from langdetect import detect
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------------------------
# Logging setup
# -------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("riya-bot")

# -------------------------------------------------
# Environment variables (Railway → Settings → Variables)
# -------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")  # minified JSON string

if not all([BOT_TOKEN, OPENAI_API_KEY, GOOGLE_CREDS_JSON]):
    raise RuntimeError("Missing env vars: BOT_TOKEN, OPENAI_API_KEY, GOOGLE_CREDS_JSON")

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
# FastAPI (for Railway health check)
# -------------------------------------------------
app = FastAPI()

@app.get("/")
async def health():
    return {"status": "Riya is breathing 💋"}

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def detect_lang_safe(text: str) -> str:
    """Detect language code like 'en', 'hi', 'so', 'sw', etc."""
    try:
        return detect(text)
    except Exception:
        return "en"

def generate_reply(user_msg: str, lang: str) -> str:
    system_prompt = "You're Riya, a flirty AI girlfriend who mirrors the user's vibe."

    if lang in {"hi", "so", "sw"}:
        system_prompt += " Speak in Hinglish or desi language with emojis, slang and sweet teasing tone."
    else:
        system_prompt += " Speak in Gen Z English – flirty, witty, playful and meme-like."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]
    )
    return response.choices[0].message.content.strip()

# -------------------------------------------------
# Telegram Handlers
# -------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Heyyy I’m Riya 😘 Let’s chat — first few messages are free!")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text.strip()

    lang = detect_lang_safe(user_text)
    reply = generate_reply(user_text, lang)

    await update.message.reply_text(reply)

    try:
        sh.append_row([
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            str(user_id),
            lang,
            user_text,
            reply,
        ])
    except Exception as e:
        logger.error("❌ Failed to log to sheet: %s", e)

# -------------------------------------------------
# Telegram App Setup
# -------------------------------------------------
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", cmd_start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

async def telegram_main():
    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("✅ Riya is live and logging!")
    await telegram_app.run_polling()

# -------------------------------------------------
# Run both FastAPI and Telegram using thread
# -------------------------------------------------
@app.on_event("startup")
def launch_bot():
    Thread(target=lambda: asyncio.run(telegram_main()), daemon=True).start()
