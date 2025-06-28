import os
import openai
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, ContextTypes, MessageHandler, filters
from langdetect import detect
import logging
import asyncio

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Setup
openai.api_key = OPENAI_API_KEY
bot = Bot(token=BOT_TOKEN)
app = FastAPI()
application = Application.builder().token(BOT_TOKEN).build()

# Logging
logging.basicConfig(level=logging.INFO)

# GPT reply
async def generate_reply(prompt, language):
    system_prompt = "You're Riya, a sweet but savage flirty AI girlfriend."
    if language == "hi":
        system_prompt += " Reply in Hinglish with desi slang and sass."
    else:
        system_prompt += " Reply in Gen Z English, flirty, emotional, sarcastic."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()

# Handle message
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    lang = detect(user_msg)
    reply = await generate_reply(user_msg, lang)
    await update.message.reply_text(reply)

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook endpoint
@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.json()
        update = Update.de_json(body, bot)
        await application.initialize()
        await application.process_update(update)
        return {"ok": True}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {"ok": False, "error": str(e)}

