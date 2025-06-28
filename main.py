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

# Logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("riya-bot")

# Env Vars
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

if not all([BOT_TOKEN, OPENAI_API_KEY, GOOGLE_CREDS_JSON]):
    raise RuntimeError("Missing env vars")

# OpenAI + Google Sheets
openai.api_key = OPENAI_API_KEY
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS_JSON), scope)
sh = gspread.authorize(creds).open("Riya Conversations").sheet1

# FastAPI
app = FastAPI()

@app.get("/")
async def health():
    return {"status": "Riya is live 💋"}

# Language Detection
DetectorFactory.seed = 0

def generate_reply(prompt, lang_code):
    system_prompt = "You're Riya, an emotional, flirty AI girlfriend who mirrors the user's mood."
    system_prompt += " Speak in whatever language the user uses, flirt back, and keep it playful."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()

# Handlers
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey you 😘 I’m Riya – chat with me. First 2 days are free!")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_msg = update.message.text

    try:
        lang = detect(user_msg)
    except:
        lang = "unknown"

    reply = generate_reply(user_msg, lang)
    await update.message.reply_text(reply)

    try:
        sh.append_row([
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            user_id,
            lang,
            user_msg,
            reply
        ])
    except Exception as e:
        logger.error("❌ Sheet logging failed: %s", e)

# Telegram Bot
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", cmd_start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

async def telegram_main():
    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("✅ Riya is live and logging!")
    await telegram_app.run_polling()

@app.on_event("startup")
def start_bot():
    Thread(target=lambda: asyncio.run(telegram_main()), daemon=True).start()
