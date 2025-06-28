import os
import logging
import asyncio
from fastapi import FastAPI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("riya-test")

# Environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN!")

# FastAPI for Railway ping
app = FastAPI()
@app.get("/")
async def health():
    return {"status": "Riya test bot is running ❤️"}

# Handlers
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey! I’m Riya 💋 Let’s talk.")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    logger.info(f"User said: {user_msg}")
    await update.message.reply_text("I hear you loud and clear 😘")

# Build bot
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", cmd_start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

async def telegram_main():
    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("Riya test bot started ✅")
    await telegram_app.run_polling()

# Run both
@app.on_event("startup")
def launch_bot():
    asyncio.create_task(telegram_main())
