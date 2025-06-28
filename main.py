import os
import asyncio
from fastapi import FastAPI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import logging

BOT_TOKEN = os.getenv("BOT_TOKEN")

app = FastAPI()  # ✅ THIS MUST EXIST

# Basic logger
logging.basicConfig(level=logging.INFO)

# Telegram bot logic
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey babe 😘 Riya is online!")

# Start polling logic
async def telegram_main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(telegram_main())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
