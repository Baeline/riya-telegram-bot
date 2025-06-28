import os
import openai
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Initialize Telegram application
bot = Bot(BOT_TOKEN)
application = Application.builder().token(BOT_TOKEN).build()

# FastAPI app
app = FastAPI()

# Telegram command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey cutie 😘 Riya is LIVE, let’s get flirty!")

application.add_handler(CommandHandler("start", start))

# Webhook route for Telegram
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return {"ok": True}
