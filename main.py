import os, json, logging, asyncio
from datetime import datetime
from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
import openai, gspread
from langdetect import detect
from oauth2client.service_account import ServiceAccountCredentials

# ── ENV ─────────────────────────────────────────────────────────
BOT_TOKEN        = os.getenv("BOT_TOKEN")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_RAW = os.getenv("GOOGLE_CREDS_JSON")   # full JSON string

# ── LOGGING ─────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("riya-bot")

# ── OPENAI ──────────────────────────────────────────────────────
openai.api_key = OPENAI_API_KEY

# ── GOOGLE SHEET ────────────────────────────────────────────────
sheet = None
try:
    scope  = ["https://spreadsheets.google.com/feeds",
              "https://www.googleapis.com/auth/drive"]
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(
                json.loads(GOOGLE_CREDS_RAW), scope)
    client = gspread.authorize(creds)
    sheet  = client.open("Riya Conversations").sheet1   # exact name!
    logger.info("✅ Connected to Google Sheet")
except Exception as e:
    logger.warning(f"Sheet disabled → {e}")

# ── FASTAPI (Railway health-check) ──────────────────────────────
app = FastAPI()
@app.get("/")
def ping():
    return {"status": "Riya is alive 💋"}

# ── GPT REPLY ───────────────────────────────────────────────────
def gpt_reply(text:str, lang:str)->str:
    system = (
        "You're Riya, a flirty, emotional Gen-Z girlfriend. "
        "Mirror the user's tone. If user writes Hinglish/Hindi, reply Hinglish; "
        "otherwise Gen-Z English. Keep it playful and concise."
    )
    if lang == "hi":
        system += " Use desi slang and cute roasts."

    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role":"system","content":system},
            {"role":"user"  ,"content":text}
        ])
    return res.choices[0].message.content.strip()

# ── TELEGRAM HANDLERS ───────────────────────────────────────────
async def cmd_start(update:Update, ctx:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey babe 😘 Riya is online!")

async def on_msg(update:Update, ctx:ContextTypes.DEFAULT_TYPE):
    txt  = update.message.text or ""
    uid  = update.effective_user.id
    lang = "en"
    try:
        lang = detect(txt)
    except Exception as e:
        logger.warning(f"🌐 Lang detect failed: {e}")

    logger.info(f"📝 User: {uid} | Msg: {txt} | Lang: {lang}")

    try:
        reply = gpt_reply(txt, lang)
        logger.info(f"💬 GPT replied: {reply}")
    except Exception as e:
        logger.error(f"❌ GPT error: {e}")
        reply = "Oops babe, I zoned out 😵"

    await update.message.reply_text(reply)

    if sheet:
        try:
            sheet.append_row([
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                str(uid), "", lang, txt, reply, ""
            ])
        except Exception as e:
            logger.warning(f"Sheet write failed: {e}")

# ── TELEGRAM APP ────────────────────────────────────────────────
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
bot_app.add_handler(CommandHandler("start", cmd_start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_msg))

# ── START POLLING WHEN CONTAINER BOOTS ─────────────────────────
# ── START BOT + CLEAN SHUTDOWN ───────────────────────────────
@app.on_event("startup")
async def startup_event():
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.bot.delete_webhook(drop_pending_updates=True)  # 💥 THIS LINE
    await bot_app.updater.start_polling()


@app.on_event("shutdown")
async def shutdown_event():
    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()


