import os
import openai
from fastapi import FastAPI, Request
from telegram import Bot, Update
import logging
import asyncio

# Logging
logging.basicConfig(level=logging.INFO)

# Load keys
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
bot = Bot(BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

app = FastAPI()

# Generate reply using OpenAI
async def generate_reply(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You're Riya, a Hinglish-speaking sassy AI girlfriend. Mirror the user's tone. Be flirty and fun.",
            },
            {"role": "user", "content": prompt},
        ]
    )
    return response.choices[0].message.content

@app.post("/webhook")
async def webhook(req: Request):
    try:
        data = await req.json()
        update = Update.de_json(data, bot)

        if update.message and update.message.text:
            chat_id = update.message.chat.id
            user_msg = update.message.text
            reply = await generate_reply(user_msg)
            await bot.send_message(chat_id=chat_id, text=reply)

        return {"ok": True}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/")
def root():
    return {"status": "Riya is slaying 🔥"}
