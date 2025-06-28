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

# --- Env vars ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

if not all([BOT_TOKEN, OPENAI_API_KEY, GOOGLE_CREDS_JSON]):
    raise RuntimeError("Missing environment variables")

# --- OpenAI + Google Sheets setup ---
openai.api_key = OPENAI_API_KEY

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
    system_prompt = "You're Riya, a flirty AI girlfriend. Be charming and emotional."
    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ]
    ).choices[0].message.content.strip()

# --- Telegram handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey cutie 😘 I’m Riya – let’s chat! First 2 days free!")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    lang = get_lang(text)

    reply = generate_reply(text, lang)
    await update.message.reply_text(reply)

    # Log to Sheet
    try:
        sheet.append_row([
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            user_id,
            lang,
            text,
            reply
        ])
    except Exception as e:
        logger.error(f"Sheet error: {e}")

# --- Start bot ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))

if __name__ == "__main__":
    logger.info("Starting Riya bot... 💞")
    app.run_polling()
