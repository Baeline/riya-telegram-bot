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
# Env variables (Railway)
# -------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

if not all([BOT_TOKEN, OPENAI_API_KEY, GOOGLE_CREDS_JSON]):
    raise RuntimeError("Missing env vars!")

# -------------------------------------------------
# Init OpenAI & Google Sheets
# -------------------------------------------------
openai.api_key = OPENAI_API_KEY

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS_JSON), scope)
sheet = gspread.authorize(creds).open("Riya Conversations").sheet1

# -------------------------------------------------
# FastAPI (health check)
# -------------------------------------------------
app = FastAPI()

@app.get("/")
async def health():
    return {"status": "Riya is breathing 💋"}

# -------------------------------------------------
# Helpers
# -------------------------------------------------
DetectorFactory.seed = 0  # makes langdetect stable

def detect_lang(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "en"

def generate_reply(user_msg: str, lang: str) -> str:
    system_prompt = "You're Riya, a flirty, emotional AI girlfriend who mirrors the user's vibe."
    if lang == "hi":
        system_prompt += " Use Hinglish, cute desi slang, sweet chaos."
    else:
        system_prompt += " Use Gen-Z flirty English, memes, and sass."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
    )
    return response.choices[0].message.content.strip()

# -------------------------------------------------
# Telegram Handlers
# -------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey you 😘 I'm Riya. First 2 days are free. Talk to me 💬")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text.strip()
    lang = detect_lang(user_text)
    reply = generate_reply(user_text, lang)

    print(f"[DEBUG] user_id={user_id}, lang={lang}, msg='{user_text}'")
    print(f"[DEBUG] reply: {reply}")

    await update.message.reply_text(reply)

    # Log conversation
    try:
        sheet.append_row([
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            user_id,
            lang,
            user_text,
            reply,
        ])
    except Exception as e:
        logger.error("Failed to log to sheet: %s", e)

# -------------------------------------------------
# Telegram App
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
# Run Telegram bot alongside FastAPI
# -------------------------------------------------
@app.on_event("startup")
import uvicorn

@app.on_event("startup")
def start_bot():
    loop = asyncio.get_event_loop()
    loop.create_task(telegram_main())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)

