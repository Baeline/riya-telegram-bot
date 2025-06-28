import os
import json
import logging
import asyncio
from datetime import datetime
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("riya-bot")

# -------------------------------------------------
# Environment variables (Railway → Settings → Variables)
# -------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")  # <-- minified JSON in env var

if not GOOGLE_CREDS_JSON:
    raise RuntimeError("GOOGLE_CREDS_JSON env var is missing – add it in Railway → Settings → Variables")

# -------------------------------------------------
# External clients
# -------------------------------------------------
openai.api_key = OPENAI_API_KEY

# Google Sheets auth (load creds from ENV instead of local file!)
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds_dict = json.loads(GOOGLE_CREDS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
sheet = gspread.authorize(creds).open("Riya Conversations").sheet1

# -------------------------------------------------
# FastAPI (for Railway health check)
# -------------------------------------------------
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Riya is live 🩷"}

# -------------------------------------------------
# Utility: Safe language detection
# -------------------------------------------------
DetectorFactory.seed = 0  # deterministic

def get_language_safe(text: str) -> str:
    try:
        if len(text.strip()) < 5:
            return "en"
        lang = detect(text)
        return lang if lang in {"en", "hi"} else "en"
    except Exception:
        return "en"

# -------------------------------------------------
# AI reply helper
# -------------------------------------------------

def generate_reply(user_text: str, language: str) -> str:
    system_prompt = "You're Riya, a flirty, emotional girlfriend who mirrors the user's mood."  # base
    if language == "hi":
        system_prompt += " Speak in Hinglish with desi GF vibes, cute slang, and emojis."  # Hindi/Hinglish style
    else:
        system_prompt += " Speak in Gen‑Z English, witty and playful."  # English style

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    )
    return response.choices[0].message.content.strip()

# -------------------------------------------------
# Telegram handlers
# -------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey you 😘 I’m Riya – chat with me, I don't bite… much!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    language = get_language_safe(user_text)

    reply = generate_reply(user_text, language)
    await update.message.reply_text(reply)

    # log to Google Sheet
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
        sheet.append_row([timestamp, user_id, language, user_text, reply])
    except Exception as e:
        logger.error("Failed to append to sheet: %s", e)

# -------------------------------------------------
# Telegram bot runner
# -------------------------------------------------

tg_app = ApplicationBuilder().token(BOT_TOKEN).build()
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def run_bot():
    await tg_app.initialize()
    await tg_app.start()
    logger.info("Riya bot started ✅")
    await tg_app.updater.start_polling()
    await tg_app.updater.idle()

asyncio.create_task(run_bot())
