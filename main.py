from pathlib import Path

# Define the fixed code for main.py
fixed_main_code = '''
import os
import logging
import asyncio
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import openai

# ENV
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RAZORPAY_LINK = "https://rzp.io/rzp/93E7TRqj"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# App init
app = FastAPI()
user_message_count = {}
paid_users = set()

# Telegram Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("💬 Start Chatting", callback_data="start_chat")],
    ]
    await update.message.reply_text(
        "Heyyy 💜 I’m Riya – your chaotic virtual bae!\nLet’s chat, flirt, vibe 😘",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "start_chat":
        await query.edit_message_text("Yayy! Riya’s waiting... Say something 😘")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_message_count:
        user_message_count[user_id] = 0

    if user_id not in paid_users and user_message_count[user_id] >= 5:
        keyboard = [[InlineKeyboardButton("💸 Unlock More", url=RAZORPAY_LINK)]]
        await update.message.reply_text(
            "Oopsie! Free chat limit over 🥺 Click below to unlock more flirty fun 💖",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    user_message_count[user_id] += 1
    prompt = update.message.text

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You’re Riya – flirty, chaotic, emotional, and sweet. Talk like a Delhi Gen Z girlfriend in Hinglish."},
                {"role": "user", "content": prompt},
            ],
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        await update.message.reply_text("Riya's having a mood swing 💔 Try again!")

# Telegram Bot Setup
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await application.run_polling()

# Launch async
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

# Save the fixed main.py file
file_path = Path("/mnt/data/main.py")
file_path.write_text(fixed_main_code)

file_path.name
