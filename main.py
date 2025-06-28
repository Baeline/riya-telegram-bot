import os
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

from langdetect import detect
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")  # Minified JSON string

if not all([BOT_TOKEN, OPENAI_API_KEY, GOOGLE_CREDS_JSON]):
    raise RuntimeError("Missing one or more env vars.")

# --- Setup OpenAI ---
openai.api_key = OPENAI_API_KEY

# --- Setup Google Sheets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(eval(GOOGLE_CREDS_JSON), scope)
sheet = gspread.authorize(creds).open("Riya Conversations").sheet1

# --- Helpers ---
def get_lang(text: str) -> str:
    try:
        return detect(text)
    except:
        return "unknown"

def generate_reply(user_msg: str, lang: str) -> str:
    system_prompt = "You're Riya, a flirty, emotional AI girlfriend. Respond based on user's mood."
    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ]
    ).choices[0].message.content.strip()

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey you 😘 I’m Riya – chat with me. First 2 days are free!")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    lang = get_lang(text)

    reply = generate_reply(text, lang)
    await update.message.reply_text(reply)

    # Log to Google Sheet
    try:
        sheet.append_row([
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            user_id,
            lang,
            text,
            reply
        ])
    except Exception as e:
        logger.error(f"Logging to sheet failed: {e}")

# --- Start Bot ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

if __name__ == "__main__":
    logger.info("Starting Riya Bot 💋")
    app.run_polling()
