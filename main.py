import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)
from langdetect import detect
from fastapi import FastAPI
from openai import OpenAI

# Logging for errors
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up Telegram + FastAPI
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey boo 😘 Riya is online and spicy!")

# Message Handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_msg = update.message.text
        lang = detect(user_msg)

        system_prompt = "You're Riya, a chaotic Gen-Z desi girlfriend who mirrors user's tone."
        if lang == "hi":
            system_prompt += " Speak in Hinglish with sass and Indian slang. No emoji unless user uses them."
        else:
            system_prompt += " Speak in spicy Gen-Z English with some attitude."

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

# Telegram Handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook Endpoint
@app.post("/webhook")
async def webhook(update: dict):
    update_obj = Update.de_json(update, telegram_app.bot)
    await telegram_app.update_queue.put(update_obj)
    return {"ok": True}

telegram_app.run_webhook(
    listen="0.0.0.0",
    port=int(os.getenv("PORT", 8000)),
    webhook_url="https://riya-telegram-bot-production.up.railway.app/webhook"
)
