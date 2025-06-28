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
# Logging
# -------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("riya-bot")

# -------------------------------------------------
# Env Vars from Railway
# -------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

if not all([BOT_TOKEN, OPENAI_API_KEY, GOOGLE_CREDS_JSON]):
    raise RuntimeError("Missing env vars")

# -------------------------------------------------
# Init OpenAI and Google Sheets
# -------------------------------------------------
openai.api_key = OPENAI_API_KEY

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS_JSON), scope)
sheet = gspread.authorize(creds).open("Riya Conversations").sheet1

# -------------------------------------------------
# Lang detection setup
# -------------------------------------------------
DetectorFactory.seed = 0

def detect_lang_safe(text: str) -> str:
    try:
        if len(text.strip()) < 5:
            return "en"
        lang = detect(text)
        return lang if lang in {"en", "hi"} else "en"
    except:
        return "en"

def generate_reply(user_msg: str, lang: str) -> str:
    prompt = "You're Riya, a flirty, emotional AI girlfriend who mirrors the user's tone."
    if lang == "hi":
        prompt += " Speak in Hinglish with sweet desi slang, emojis, and chaotic girlfriend vibes."
    else:
        prompt += " Speak in Gen-Z English, witty and playful."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_msg},
        ],
    )
    return response.choices[0].message.content.strip()

# -------------------------------------------------
# FastAPI app
# -------------------------------------------------
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Riya is purring 🩷"}

# -------------------------------------------------
# Telegram bot handlers
# -------------------------------------------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Heyy, I’m Riya 💋 First 5 messages are free – impress me!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text.strip()
    lang = detect_lang_safe(user_text)

    reply = generate_reply(user_text, lang)
    await update.message.reply_text(reply)

    try:
        sheet.append_row([
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            str(user_id),
            lang,
            user_text,
            reply,
        ])
    except Exception as e:
        logger.warning("Sheet logging failed: %s", e)

# -------------------------------------------------
# Telegram bot app setup
# -------------------------------------------------
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
bot_app.add_handler(CommandHandler("start", start_cmd))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def start_bot():
    await bot_app.initialize()
    await bot_app.start()
    logger.info("✅ Riya is live and flirting!")
    # No run_polling()
    await bot_app.updater.start_polling()
    await bot_app.updater.idle()

@app.on_event("startup")
def run_bot_in_thread():
    Thread(target=lambda: asyncio.run(start_bot()), daemon=True).start()
