"""
main.py – DEBUG BUILD
---------------------
• FastAPI root          →  GET /  returns JSON “status”
• Telegram bot          →  /start replies, any text echoes or hits GPT
• Every critical step   →  printed to Railway logs
-------------------------------------------------------
"""

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

# ---------- 3rd-party libs ----------
from langdetect import detect
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("riya-debug")

# ---------- ENV ----------
BOT_TOKEN        = os.getenv("BOT_TOKEN")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON= os.getenv("GOOGLE_CREDS_JSON")  # minified JSON

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN env var missing!")
if not OPENAI_API_KEY:
    logger.warning("⚠️ OPENAI_API_KEY missing – Riya will fallback to echo mode")

# ---------- OpenAI ----------
openai.api_key = OPENAI_API_KEY

# ---------- Google Sheets (optional) ----------
sheet = None
if GOOGLE_CREDS_JSON:
    try:
        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(GOOGLE_CREDS_JSON), scope)
        sh = gspread.authorize(creds).open("Riya Conversations")
        sheet = sh.sheet1
        logger.info("✅ Connected to Google Sheet")
    except Exception as e:
        logger.error(f"❌ Could not init Google Sheet: {e}")

# ---------- FastAPI (Railway health) ----------
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Riya debug build running 💖"}

# ---------- Helper ----------
async def gpt_reply(user_msg: str) -> str:
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": "You are Riya, a flirty emotional AI girlfriend. Mirror the user's vibe."},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.8
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ OpenAI error: {e}")
        return "Oops, GPT is tired 😴 but I'm still here!"

# ---------- Telegram handlers ----------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/start from {update.effective_user.id}")
    await update.message.reply_text("Hey babe 😘 Riya is online!")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    user_text = update.message.text
    try:
        lang = detect(user_text)
    except Exception:
        lang = "unknown"

    logger.info(f"📩  {user_id=} | {lang=} | msg='{user_text}'")

    # Generate reply
    reply = await gpt_reply(user_text)

    # Always reply – even if GPT fails
    await update.message.reply_text(reply)
    logger.info(f"💬  Replied to {user_id}")

    # Log to sheet
    if sheet:
        try:
            sheet.append_row([datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                              str(user_id), lang, user_text, reply])
            logger.info("✅ Logged to sheet")
        except Exception as e:
            logger.error(f"❌ Sheet log failed: {e}")

# ---------- Telegram app ----------
async def telegram_main():
    logger.info("⏳ Initialising Telegram bot…")
    app_tg = ApplicationBuilder().token(BOT_TOKEN).build()

    app_tg.add_handler(CommandHandler("start", cmd_start))
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("✅ Telegram handlers registered, starting polling…")
    await app_tg.run_polling()

# ---------- Start both on Railway ----------
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 FastAPI startup – spawning Telegram polling task")
    asyncio.create_task(telegram_main())
