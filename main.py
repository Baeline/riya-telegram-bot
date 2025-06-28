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
# Environment variables (Railway → Settings → Variables)
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
# FastAPI (health‑check endpoint)
# -------------------------------------------------
app = FastAPI()

@app.get("/")
async def health():
    return {"status": "Riya is purring 🩷"}

# -------------------------------------------------
# Helpers
# -------------------------------------------------
DetectorFactory.seed = 0  # deterministic

def detect_lang_safe(text: str) -> str:
    """Return 'en' or 'hi' (Hinglish) – default to en if unsure."""
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
        system_prompt += " Speak in Gen‑Z English, witty and playful."

    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
    )
    return resp.choices[0].message.content.strip()

# -------------------------------------------------
# Telegram handlers
# -------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey you 😘 I’m Riya – chat with me. First 2 days are free!")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    lang = detect_lang_safe(user_text)

    reply = generate_reply(user_text, lang)
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
    except Exception as e:
        logger.error("Sheet append failed: %s", e)

# -------------------------------------------------
# Build Telegram application
# -------------------------------------------------
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", cmd_start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

async def telegram_main():
    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("Riya bot started ✅ (polling)")
    await telegram_app.run_polling()

# -------------------------------------------------
# Start Telegram bot parallel to FastAPI using a thread
# -------------------------------------------------
@app.on_event("startup")
def launch_bot():
    Thread(target=lambda: asyncio.run(telegram_main()), daemon=True).start()
