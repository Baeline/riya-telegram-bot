import os
import logging
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from fastapi import FastAPI, Request
import openai

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY
bot = Bot(BOT_TOKEN)

# FastAPI app
app = FastAPI()

# Telegram bot application
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Reply generator using OpenAI
async def generate_reply(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You're Riya — a flirty, sassy, desi girlfriend. Speak in Hinglish, mirror user's tone. Keep it spicy."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# Telegram message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    reply = await generate_reply(user_text)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=reply)

telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook route
@app.post("/webhook")
async def webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, bot)
    await telegram_app.process_update(update)
    return {"ok": True}

# Health check
@app.get("/")
async def root():
    return {"status": "Riya is slaying 💅"}

# Run Telegram bot polling (not needed in webhook mode, just for local testing)
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Riya on port 8080...")
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
