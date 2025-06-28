import os
import openai
from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import logging

# Logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# FastAPI app
app = FastAPI()
bot = Bot(BOT_TOKEN)

# OpenAI response generator
async def generate_reply(user_msg):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You're Riya, a flirty, sassy virtual girlfriend who speaks in Hinglish. Mirror the user's tone and vibe.",
            },
            {"role": "user", "content": user_msg}
        ]
    )
    return response['choices'][0]['message']['content']

# Telegram webhook endpoint
@app.post("/webhook")
async def receive_update(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, bot)

        if update.message and update.message.text:
            user_msg = update.message.text
            chat_id = update.message.chat.id

            reply = await generate_reply(user_msg)
            await bot.send_message(chat_id=chat_id, text=reply)

        return {"ok": True}
    except Exception as e:
        logging.error(f"Error: {e}")
        return {"ok": False, "error": str(e)}

# Optional health check
@app.get("/")
def read_root():
    return {"message": "Riya is live 💖"}
