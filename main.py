from pathlib import Path

# Final patched main.py content with correct sheet name and safety checks
final_main_py = """
import os
import logging
from fastapi import FastAPI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import openai
from langdetect import detect
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

# Set OpenAI key
openai.api_key = OPENAI_API_KEY

# FastAPI app for health checks
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Riya is up and running!"}

# Authenticate Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(eval(GOOGLE_CREDS_JSON), scope)
client = gspread.authorize(creds)

# Open sheet safely
try:
    sheet = client.open("Riya Conversations").sheet1
except Exception as e:
    logger.error(f"❌ Google Sheet Error: {e}")
    sheet = None

# Generate reply using OpenAI
def generate_reply(prompt, language):
    system_prompt = "You're Riya, a bilingual, flirty girlfriend who mirrors user's mood."

    if language == "hi":
        system_prompt += " Speak in Hinglish with Hindi slang and affectionate tone."
    else:
        system_prompt += " Speak in playful Gen-Z English. Add emojis only if user does."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# Handle start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey babe 😘 Riya is online!")

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    user_id = update.message.from_user.id
    lang = detect(user_msg)
    logger.info(f"Message from {user_id}: {user_msg} | Lang: {lang}")

    try:
        reply = generate_reply(user_msg, lang)
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        reply = "Oops babe, I zoned out 😵"

    await update.message.reply_text(reply)

    if sheet:
        try:
            sheet.append_row([update.message.date.isoformat(), user_id, "", lang, user_msg, reply, ""])
        except Exception as e:
            logger.warning(f"Sheet write failed: {e}")

# Set up Telegram bot
app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.on_event("startup")
async def startup():
    import asyncio
    asyncio.create_task(app_bot.run_polling())
"""

# Save to file
main_path = Path("/mnt/data/main.py")
main_path.write_text(final_main_py)

main_path.name
