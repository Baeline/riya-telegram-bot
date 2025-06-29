import os, json, logging, asyncio
from datetime import datetime
from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)
import openai, gspread
from langdetect import detect
from oauth2client.service_account import ServiceAccountCredentials

# ── ENV ─────────────────────────────────────────────
BOT_TOKEN        = os.getenv("BOT_TOKEN")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_RAW = os.getenv("GOOGLE_CREDS_JSON")

# ── LOGGING ─────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("riya-bot")

# ── OpenAI Setup ────────────────────────────────────
openai.api_key = OPENAI_API_KEY

# ── Google Sheets Setup ─────────────────────────────
sheet = None
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS_RAW), scope)
    client = gspread.authorize(creds)
    sheet = client.open("Riya Conversations").sheet1
    logger.info("✅ Connected to Google Sheet")
except Exception as e:
    logger.warning(f"⚠️ Google Sheet not connected → {e}")

# ── FastAPI (for Railway health check) ──────────────
app = FastAPI()
@app.get("/")
def ping():
    return {"status": "Riya is alive 💋"}

# ── OpenAI GPT Logic ────────────────────────────────
async def gpt_reply(prompt: str, lang: str) -> str:
    try:
        system_msg = (
            "You're Riya, a flirty, emotional Gen-Z girlfriend. "
            "Mirror the user's tone. If user writes Hinglish/Hindi, reply Hinglish; "
            "otherwise Gen-Z English. Keep it playful and concise."
        )
        if lang == "hi":
            system_msg += " Use desi slang and cute roasts."

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ GPT error: {e}")
        return "Oops babe, I zoned out 😵"

# ── Telegram Handlers ───────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey babe 😘 Riya is online!")

async def on_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    uid = update.effective_user.id
    lang = "en"
    try:
        lang = detect(text)
    except:
        pass

    reply = await gpt_reply(text, lang)
    await update.message.reply_text(reply)

    if sheet:
        try:
            sheet.append_row([
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                str(uid), "", lang, text, reply, ""
            ])
        except Exception as e:
            logger.warning(f"⚠️ Failed to write to sheet: {e}")

# ── Telegram Bot App ────────────────────────────────
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
bot_app.add_handler(CommandHandler("start", cmd_start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_msg))

# ── Lifecycle Hooks for Railway ─────────────────────
@app.on_event("startup")
async def startup():
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()
    logger.info("✅ Riya started successfully.")

@app.on_event("shutdown")
async def shutdown():
    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()
    logger.info("👋 Riya shut down.")
