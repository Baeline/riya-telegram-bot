import os
import logging
from fastapi import FastAPI
from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI
from langdetect import detect

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI setup
client = OpenAI(api_key=OPENAI_API_KEY)

# FastAPI app (to keep Railway alive)
app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Riya is live and flirting 💋"}

# Function to generate a flirty reply
async def generate_reply(prompt: str, language: str) -> str:
    system_prompt = (
        "You are Riya — a playful, emotional, bilingual virtual girlfriend. "
        "Mirror user's tone. Speak in Hinglish if the message is Hindi or Hinglish. "
        "Flirt back, roast gently, and keep it casual and Gen Z."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.8,
    )

    return response.choices[0].message.content.strip()

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey babe 😘 Riya is online!")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.effective_user.id

    try:
        lang = detect(user_message)
    except:
        lang = "en"

    logger.info(f"Message from {user_id} | Language: {lang} | Text: {user_message}")

    reply = await generate_reply(user_message, lang)
    await update.message.reply_text(reply)

# Main function
async def telegram_main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Riya is live and logging!")
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(telegram_main())
