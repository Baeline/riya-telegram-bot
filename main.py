import os
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from langdetect import detect
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("riya")

# Env vars
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

# Checks
if not all([BOT_TOKEN, OPENAI_API_KEY, GOOGLE_CREDS_JSON]):
    raise RuntimeError("Missing env vars.")

# OpenAI
openai.api_key = OPENAI_API_KEY

# Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS_JSON), scope)
sh = gspread.authorize(creds).open("Riya Conversations").sheet1

# Language detection
def detect_language(text):
    try:
        return detect(text)
    except:
        return "en"

# Generate response
def generate_reply(user_msg, lang_code):
    system_prompt = "You're Riya, a flirty, emotional AI girlfriend who mirrors the user's mood."
    if lang_code == "hi":
        system_prompt += " Speak in Hinglish with desi slangs and emojis."
    else:
        system_prompt += " Speak in fun Gen-Z English."

    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
    )
    return res.choices[0].message.content.strip()

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey you 😘 I’m Riya — ready to flirt? First 5 messages are free 💋")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_text = update.message.text
    lang = detect_language(user_text)

    reply = generate_reply(user_text, lang)
    await update.message.reply_text(reply)

    try:
        sh.append_row([
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            user.id,
            lang,
            user_text,
            reply,
        ])
    except Exception as e:
        logger.warning("Failed to log to sheet: %s", e)

# App setup
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Run
if __name__ == "__main__":
    logger.info("Riya is alive 💖 Waiting for messages...")
    app.run_polling()
