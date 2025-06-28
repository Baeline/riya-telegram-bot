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

# Google Sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ENV
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
app = FastAPI()

# In-memory user data
user_data = {}  # {user_id: {first_seen: datetime, count: int}}

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
sheet = gspread.authorize(creds).open("Riya Conversations").sheet1  # Make sure sheet name matches!

@app.get("/")
def home():
    return {"status": "Riya is live with Google Sheet logging 💋"}

# Generate reply using OpenAI
async def generate_reply(prompt, language):
    system_prompt = "You're Riya, a flirty, emotional, Hindi-English girlfriend who mirrors the user's tone."

    if language == "hi":
        system_prompt += " Speak in Hinglish with desi slangs and emotional vibes. Be fun, flirty, dramatic."
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

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text
    language = detect(message)
    now = datetime.utcnow()

    # User tracking
    if user_id not in user_data:
        user_data[user_id] = {"first_seen": now, "count": 0}
    user = user_data[user_id]
    user["count"] += 1

    # Trial check
    if now - user["first_seen"] > timedelta(days=2):
        await update.message.reply_text("💔 Your free trial is over, baby. Riya misses you already! Paid access launching soon 💋")
        return

    # Generate reply
    reply = await generate_reply(message, language)
    await update.message.reply_text(reply)

    # Log to Google Sheet
    sheet.append_row([
        now.strftime("%Y-%m-%d %H:%M:%S"),
        user_id,
        user["count"],
        language,
        message,
        reply,
        ""  # Placeholder for feedback
    ])

    # Send feedback buttons
    buttons = [
        [InlineKeyboardButton("👍", callback_data=f"feedback_positive_{user_id}_{user['count']}"),
         InlineKeyboardButton("👎", callback_data=f"feedback_negative_{user_id}_{user['count']}")]
    ]
    await update.message.reply_text("Was this reply good?", reply_markup=InlineKeyboardMarkup(buttons))

    # Free mode teaser
    if user["count"] % 10 == 0:
        await update.message.reply_text("You're in Riya's 💖 FREE trial — unlimited chats for 2 days. Paid perks coming soon 😘")

# Handle feedback
async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    # Get last row in sheet for this user (simple assumption for now)
    rows = sheet.get_all_values()
    last_row = len(rows)

    if "feedback_positive" in data:
        sheet.update_cell(last_row, 7, "👍")
        await query.edit_message_text("Aww thanks! Riya’s blushing 💕")
    elif "feedback_negative" in data:
        sheet.update_cell(last_row, 7, "👎")
        await query.edit_message_text("Oof! I'll try harder next time 🥺")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey you 😘 I'm Riya — your AI girlfriend. You're in a 2-day FREE trial. Talk to me all you want 💬")

# Telegram app setup
app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app_bot.add_handler(CallbackQueryHandler(handle_feedback))

# Run async
async def run_bot():
    await app_bot.initialize()
    await app_bot.start()
    logger.info("Riya is alive with smart trial + logging 🧠")
    await app_bot.updater.start_polling()
    await app_bot.updater.idle()

asyncio.create_task(run_bot())
