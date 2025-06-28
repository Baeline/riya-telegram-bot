import os
import asyncio
import logging
from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)
from langdetect import detect
from openai import OpenAI

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env vars
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Create OpenAI client for sk-proj keys
client = OpenAI(api_key=OPENAI_API_KEY)

# FastAPI + Telegram setup
app = FastAPI()
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey boo 😘 Riya is online and spicy!")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_msg = update.message.text
        lang = detect(user_msg)

        system_prompt = "You're Riya, a spicy Gen-Z desi girlfriend who mirrors user's tone."
        if lang == "hi":
            system_prompt += " Speak in Hinglish with sass, slang, and flirty energy."
        else:
            system_prompt += " Speak in Gen-Z English with chaotic confidence and flirtiness."

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ]
        )

        reply = response.choices[0].message.content
        await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        await update.message.reply_text("Aww, Riya is confused right now 😔 Try again later?")

# Add handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# FastAPI webhook endpoint
@app.post("/webhook")
async def telegram_webhook(update: dict):
    logger.info("Received update from Telegram")
    update_obj = Update.de_json(update, telegram_app.bot)
    await telegram_app.update_queue.put(update_obj)
    return {"ok": True}

# Launch Telegram bot async inside FastAPI
@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.start()



@app.on_event("shutdown")
async def shutdown():
    await telegram_app.stop()
