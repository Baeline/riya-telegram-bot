import os
import logging
import openai
import asyncio
import json
from fastapi import FastAPI
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from langdetect import detect
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ENV variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

# Set API key
openai.api_key = OPENAI_API_KEY

# Init Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_CREDS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Riya Logs").sheet1

# Log to Sheet
def log_to_sheet(user_id, lang_code, user_msg, reply, message_count=1):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([timestamp, str(user_id), message_count, lang_code, user_msg, reply, ""])

# Generate reply
async def generate_reply(prompt, language):
    system_prompt = "You're Riya — a flirty, emotional, bilingual GenZ girlfriend who mirrors user's tone."
    if language == "hi":
        system_prompt += " Speak Hinglish with desi slang, mix Hindi & English naturally."
    else:
        system_prompt += " Speak GenZ English and flirt like a fun, confident AI babe 😘"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content']

# Start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey babe 😘 Riya is online!")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    user_id = update.effective_user.id
    message_count = 1  # You can replace this with your own tracking logic

    try:
        lang_code = detect(user_msg)
    except:
        lang_code = "en"

    try:
        reply = await generate_reply(user_msg, lang_code)
        await update.message.reply_text(reply)
        log_to_sheet(user_id, lang_code, user_msg, reply, message_count)
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text("Oops babe, I zoned out 😵")

# FastAPI
app = FastAPI()

@app.on_event("startup")
async def startup():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Optional: Set bot commands
    await application.bot.set_my_commands([
        BotCommand("start", "Wake Riya up 😘")
    ])

    logger.info("✅ Riya is live and logging!")

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
