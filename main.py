import os
import openai
from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import logging
import asyncio

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Initialize bot and FastAPI
bot = Bot(BOT_TOKEN)
app = FastAPI()

# OpenAI reply generator
async def generate_reply(user_message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You're Riya, a flirty, sassy, smart virtual girlfriend who speaks in Hinglish. Mirror the user's tone."},
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.content.strip()

# Telegram webhook endpoint
@app.post("/webhook")
async def telegram_webhook(req: Request):
    try:
        data = await req.json()
        update = Update.de_json(data, bot)

        if update.message and update.message.text:
            user_msg = update.message.text
            chat_id = update.message.chat.id

            reply = await generate_reply(user_msg)
            await bot.send_message(chat_id=chat_id, text=reply)

        return {"ok": True}
    except Exception as e:
        logger.error(f"Error handling update: {e}")
        return {"ok": False}

# Optional: health check
@app.get("/")
def home():
    return {"status": "Riya is live"}
