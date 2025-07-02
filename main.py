from pathlib import Path

# Clean and corrected version of main.py
fixed_main_code = '''
import os
import logging
import asyncio
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI
import requests
import json

# ENV Vars
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")

# Constants
PAYMENT_LINK = "https://rzp.io/rzp/93E7TRqj"
LOG_SHEET_URL = "https://sheet.best/api/sheets/xxxxxxxxxx"  # Replace if needed

# Init
app = FastAPI()
openai = OpenAI(api_key=OPENAI_API_KEY)
logging.basicConfig(level=logging.INFO)

# Memory Store
user_message_count = {}
paid_users = set()

# Riya Prompt
def build_prompt(user_input):
    return [
        {"role": "system", "content": "You're Riya – Delhi’s sassiest virtual bae. You flirt, tease, comfort, and mirror tone. Keep it spicy but lovable."},
        {"role": "user", "content": user_input}
    ]

# AI Reply
async def generate_reply(user_input):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=build_prompt(user_input)
    )
    return response.choices[0].message.content.strip()

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Heyyy 💜 I’m Riya – your chaotic virtual bae!\n\nLet’s chat, flirt, vibe 😘")

# Razorpay Webhook Endpoint
@app.post("/webhook")
async def handle_payment_webhook(request: Request):
    payload = await request.json()
    logging.info("Webhook payload: %s", json.dumps(payload))
    try:
        if payload.get("event") == "payment.captured":
            contact = payload["payload"]["payment"]["entity"]["email"]
            if contact:
                paid_users.add(contact)
                logging.info(f"✅ Payment received and added: {contact}")
    except Exception as e:
        logging.error(f"Webhook error: {e}")
    return {"status": "ok"}

# Message Handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Check paid status
    if user_id in paid_users:
        pass
    else:
        count = user_message_count.get(user_id, 0)
        if count >= 5:
            keyboard = [
                [InlineKeyboardButton("💸 Unlock More Chats", url=PAYMENT_LINK)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Your free chats are over 😭 Time to show me some love 💕", reply_markup=reply_markup)
            return
        user_message_count[user_id] = count + 1

    # Typing + Reply
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply = await generate_reply(text)
    await update.message.reply_text(reply)

    # Optional Logging
    try:
        requests.post(LOG_SHEET_URL, json={
            "user_id": user_id,
            "message": text,
            "reply": reply
        })
    except:
        pass

# Telegram Bot Runner
async def main():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    await app_bot.initialize()
    await app_bot.start()
    await app_bot.updater.start_polling()
    await app_bot.idle()

loop = asyncio.get_event_loop()
loop.create_task(main())
'''

# Save to file
file_path = Path("/mnt/data/main.py")
file_path.write_text(fixed_main_code)

file_path.name
