import os, logging, json, hmac, hashlib, asyncio
from collections import defaultdict

from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, AIORateLimiter,
    CommandHandler, MessageHandler, ContextTypes, filters
)
import openai

# ========== ENVIRONMENT ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# ========== LOGGING ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== STATE ==========
user_messages = defaultdict(int)
FREE_LIMIT = 5

# ========== TELEGRAM APP ==========
tg_app = Application.builder().token(BOT_TOKEN).rate_limiter(AIORateLimiter()).build()

# ========== OPENAI GPT FUNCTION ==========
async def generate_reply(prompt: str) -> str:
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You're Riya – a flirty, emotional Indian girlfriend who simps, roasts, and teases the user."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "Uff, I'm feeling moody 😒. Try again later?"

# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Heyyy 😘 I’m Riya. First 5 messages are free, toh let's gooo 💃")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_messages[user_id] >= FREE_LIMIT:
        keyboard = [
            [InlineKeyboardButton("💸 Unlock More", url="https://rzp.io/l/baeline-starter")]
        ]
        await update.message.reply_text(
            "Oops 😜 Your free chats are over!\nWanna keep talking to me?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    prompt = update.message.text
    reply = await generate_reply(prompt)
    await update.message.reply_text(reply)

    user_messages[user_id] += 1

# ========== FASTAPI SETUP ==========
app = FastAPI()

@app.on_event("startup")
async def startup():
    # Just initializes telegram bot in webhook mode
    if not tg_app.running:
        await tg_app.initialize()

@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()

    # Ensure initialized (double safety)
    if not tg_app.running:
        await tg_app.initialize()

    await tg_app.process_update(Update.de_json(data, tg_app.bot))
    return {"ok": True}

# ========== ROUTES ==========
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
