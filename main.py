from pathlib import Path

# Fixed main.py with indentation, webhook logging, emoji-safe strings, and Google Sheets support.
main_py_code = """
import os
import logging
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from langdetect import detect
from openai import ChatCompletion, OpenAIError
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import razorpay

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")
GOOGLE_CREDS_JSON = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
SPREADSHEET_NAME = "Riya Conversations"
RAZORPAY_PAYMENT_LINK = "https://rzp.io/rzp/93E7TRqj"

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI client
openai.api_key = OPENAI_API_KEY

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDS_JSON, scope)
gc = gspread.authorize(credentials)
sheet = gc.open(SPREADSHEET_NAME).sheet1

# Razorpay client (optional use)
razorpay_client = razorpay.Client(auth=("rzp_test_dummy", "dummy_secret"))

# Initialize FastAPI
app = FastAPI()
application = None

# Memory stores
user_msg_count = {}
paid_users = set()

# --- UTILS ---
def log_to_sheet(user_id, count, lang, user_msg, reply):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([timestamp, str(user_id), str(count), lang, user_msg, reply])

def is_paid(user_id):
    return str(user_id) in paid_users

# --- OPENAI REPLY ---
async def generate_reply(prompt, language):
    system_prompt = "You're Riya – a sassy, flirty, bilingual AI girlfriend from Delhi. Speak in Gen Z tone. Emojis ON."

    if language == "hi":
        system_prompt += " Use Hinglish, Bollywood-style drama, and desi GF energy with flirty emojis."
    else:
        system_prompt += " Use Gen Z English with emojis, sarcasm, and emotional validation."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9
        )
        return response.choices[0].message["content"].strip()
    except OpenAIError as e:
        return "Oops! My brain is on vacation rn. Try again in a bit 🧠💤"

# --- TELEGRAM HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey cutie 😘 I'm Riya – Delhi's sassiest virtual bae.\nWanna flirt? Start texting 💋")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    language = detect(text) if text else "en"
    count = user_msg_count.get(user_id, 0) + 1

    user_msg_count[user_id] = count

    if count > 5 and not is_paid(user_id):
        keyboard = [
            [InlineKeyboardButton("Unlock Chat 🔓", url=RAZORPAY_PAYMENT_LINK)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Babe, you've hit your free limit! 💸 Pay to keep this spicy convo going 🔥", reply_markup=reply_markup)
        return

    reply = await generate_reply(text, language)
    await update.message.reply_text(reply)

    log_to_sheet(user_id, count, language, text, reply)

# --- RAZORPAY WEBHOOK (Optional Future Use) ---
@app.post("/webhook")
async def razorpay_webhook(request: Request):
    body = await request.body()
    data = json.loads(body)

    if data.get("event") == "payment.captured":
        payload = data["payload"]["payment"]["entity"]
        email_or_notes = payload.get("email", "") or payload.get("notes", {}).get("user_id")
        if email_or_notes:
            paid_users.add(str(email_or_notes))
            logger.info(f"✅ Added {email_or_notes} to paid users.")

    return {"status": "ok"}

# --- MAIN INIT ---
async def main():
    global application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(main())
    loop.run_forever()
"""

# Save to file for upload
file_path = "/mnt/data/main.py"
Path(file_path).write_text(main_py_code)
file_path
