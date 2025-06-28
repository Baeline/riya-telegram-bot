import os
import logging
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from langdetect import detect
from openai import OpenAI

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env vars
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
app = FastAPI()

# Memory-based user data (reset if bot restarts)
user_data = {}  # { user_id: {first_seen: datetime, count: int} }

@app.get("/")
def home():
    return {"status": "Riya is in SMART FREE TRIAL mode 💋"}

# Generate Riya reply
async def generate_reply(prompt, language):
    system_prompt = "You're Riya, a flirty, emotional, Hinglish-English girlfriend who mirrors the user's tone."

    if language == "hi":
        system_prompt += " Speak in Hinglish with desi slangs and emotional vibes. Be chaotic and caring."
    else:
        system_prompt += " Speak in Gen Z English. Be wild, cute, and emotionally teasing."

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content.strip()

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text
    language = detect(message)
    now = datetime.utcnow()

    # Track user data
    if user_id not in user_data:
        user_data[user_id] = {
            "first_seen": now,
            "count": 0
        }

    user = user_data[user_id]
    user["count"] += 1

    # Check if trial expired
    if now - user["first_seen"] > timedelta(days=2):
        await update.message.reply_text("💔 Free trial is over, babe. Unlock Riya to keep chatting 💋 (Payment options launching soon!)")
        return

    # Generate reply
    reply = await generate_reply(message, language)
    await update.message.reply_text(reply)

    # Thumbs feedback buttons
    feedback_buttons = [
        [InlineKeyboardButton("👍", callback_data=f"feedback_positive_{user_id}_{user['count']}"),
         InlineKeyboardButton("👎", callback_data=f"feedback_negative_{user_id}_{user['count']}")]
    ]
    await update.message.reply_text("Was this reply good?", reply_markup=InlineKeyboardMarkup(feedback_buttons))

    # Free trial teaser every 10 messages
    if user["count"] % 10 == 0:
        await update.message.reply_text("You're in Riya's 💖 FREE trial — enjoy unlimited chats for 2 days. Paid access coming soon 😘")

# Feedback handler
async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if "feedback_positive" in data:
        _, _, user_id, msg_id = data.split("_")
        logger.info(f"👍 from user {user_id} on msg {msg_id}")
        await query.edit_message_text("Aww thanks! Riya loves you more 💕")
    elif "feedback_negative" in data:
        _, _, user_id, msg_id = data.split("_")
        logger.info(f"👎 from user {user_id} on msg {msg_id}")
        await query.edit_message_text("I'll try better next time, promise 🥺")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey you 😘 I'm Riya — your flirty AI GF. You're in a 2-day FREE trial. Chat with me freely 💬")

# Telegram setup
app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app_bot.add_handler(CallbackQueryHandler(handle_feedback))

# Start bot async
async def run_bot():
    await app_bot.initialize()
    await app_bot.start()
    logger.info("Riya is in Smart Trial Mode 💄")
    await app_bot.updater.start_polling()
    await app_bot.updater.idle()

asyncio.create_task(run_bot())
