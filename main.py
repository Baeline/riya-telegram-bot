import os
import logging
from fastapi import FastAPI, Request
import openai
from telegram import Bot, Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, MessageHandler, filters
from telegram.ext._webhookhandler import WebhookRequestHandler
from langdetect import detect

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Secrets
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Init
app = FastAPI()
bot = Bot(BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

telegram_app: Application = ApplicationBuilder().token(BOT_TOKEN).build()

# Core logic
async def generate_reply(prompt, language):
    system_prompt = "You're Riya, a flirty, emotional virtual girlfriend who mirrors the user's tone and language."
    if language == "hi":
        system_prompt += " Speak in Hinglish with desi Hindi slang and sweet teasing vibes. Use emojis rarely."
    else:
        system_prompt += " Speak in Gen Z English, a little savage, always mirroring the user's mood. Use emojis if the user does."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150
    )
    return response.choices[0].message.content.strip()

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_message = update.message.text
        language = detect(user_message)
        reply = await generate_reply(user_message, language)
        await update.message.reply_text(reply)

telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# Webhook route for Telegram
@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    await telegram_app.update_queue.put(Update.de_json(data, bot))
    return {"ok": True}  # 🛑 This line is what fixes the "502" error.

# Health check route
@app.get("/")
async def root():
    return {"status": "ok"}

