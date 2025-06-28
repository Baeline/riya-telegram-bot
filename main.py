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
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------------------------
# Logging setup
# -------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("riya-bot")

# -------------------------------------------------
# Env variables
# -------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

if not all([BOT_TOKEN, OPENAI_API_KEY, GOOGLE_CREDS_JSON]):
    raise RuntimeError("One or more env vars missing!")

# -------------------------------------------------
# Init OpenAI + Google Sheet
# -------------------------------------------------
openai.api_key = OPENAI_API_KEY

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS_JSON), scope)
sh = gspread.authorize(creds).open("Riya Conversations").sheet1

# -------------------------------------------------
# FastAPI for health check
# -------------------------------------------------
app = FastAPI()

@app.get("/")
async def health():
    return {"status": "Riya is online 💖"}

# -------------------------------------------------
# OpenAI Reply
# -------------------------------------------------
def generate_reply(user_msg: str) -> str:
    system_prompt = "You're Riya, a flirty emotional AI girlfriend who mirrors user's mood in Gen Z English."
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
    await update.message.reply_text("Hey boo 😘 I’m Riya – your AI girlfriend. Let’s chat!")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = update.effective_user.id
    user_text = update.message.text

    logger.info(f"Msg from {user_id}: {user_text}")

    reply = generate_reply(user_text)
    await update.message.reply_text(reply)

    # Logging to Sheet
    try:
        sh.append_row([
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            user_id,
            user_text,
            reply,
        ])
        logger.info("Logged to sheet ✅")
    except Exception as e:
        logger.error(f"❌ Failed to log: {e}")

# -------------------------------------------------
# Telegram app
# -------------------------------------------------
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", cmd_start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

async def telegram_main():
    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("✅ Riya is live and working (polling mode)")
    await telegram_app.run_polling()

@app.on_event("startup")
def launch_bot():
    Thread(target=lambda: asyncio.run(telegram_main()), daemon=True).start()
