# -------------------------------------------------------------
#  RIYA TELEGRAM BOT ✨  WITH GOOGLE SHEETS LOGGING
# -------------------------------------------------------------
#  • Logs chats to Google Sheet
#  • Unlimited free sassy conversations 🔥
# -------------------------------------------------------------
import os, logging, json, asyncio
from collections import defaultdict
from datetime import datetime
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application, AIORateLimiter,
    CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ───────────────────────── ENV ───────────────────────────────
BOT_TOKEN         = os.getenv("BOT_TOKEN")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
ADMIN_USER_ID     = int(os.getenv("ADMIN_USER_ID", "0"))
SHEET_ID          = os.getenv("SHEET_ID")
SHEET_NAME        = os.getenv("SHEET_NAME", "Sheet1")

if not all([BOT_TOKEN, OPENAI_API_KEY, SHEET_ID]):
    raise RuntimeError("❌ Missing one or more required env variables.")

openai.api_key = OPENAI_API_KEY

# ──────────────────────── SHEET INIT ─────────────────────────
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.getenv("GOOGLE_CREDS_JSON")
creds_data = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_data, scope)
sheet_client = gspread.authorize(creds)
sheet = sheet_client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

def log_to_sheet(user_id, user_msg, riya_reply):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, user_id, user_msg, riya_reply]
        sheet.append_row(row)
    except Exception as e:
        logging.error("❌ Sheet log error: %s", e)

# ──────────────────────── FASTAPI + PTB ──────────────────────
app = FastAPI()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
tg_app = (
    Application.builder()
    .token(BOT_TOKEN)
    .rate_limiter(AIORateLimiter())
    .concurrent_updates(True)
    .build()
)

# ──────────────────────── GPT RESPONSE ──────────────────────────
async def gpt_reply(prompt: str) -> str:
    try:
        res = await asyncio.to_thread(
            openai.ChatCompletion.create,
            model="gpt-3.5-turbo",
            temperature=0.9,
            messages=[
                {"role": "system", "content": "You're Riya – a flirty Indian girlfriend who roasts and simps."},
                {"role": "user", "content": prompt},
            ],
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        logging.error("GPT error: %s", e)
        return "Oops, lag ho gaya 😵‍💫 Try again later!"

# ──────────────── Admin Command: Manual Unlock ──────────────
async def unlock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Not allowed.")
        return
    await update.message.reply_text("(Payment disabled mode) Unlock not required 💸")

# ──────────────────── Handlers ───────────────────────────────
async def start(update: Update, _):
    await update.message.reply_text("Heyy, I'm Riya 😘 – I'm all yours, unlimited chat unlocked!")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reply = await gpt_reply(update.message.text)
    await update.message.reply_text(reply)
    log_to_sheet(user_id, update.message.text, reply)

# ──────────────────── Webhooks ───────────────────────────────
@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()
    await tg_app.process_update(Update.de_json(data, tg_app.bot))
    return {"ok": True}

# ──────────────────── Launch ────────────────────────────────
@app.on_event("startup")
async def on_startup():
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("unlock", unlock_command))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    await tg_app.initialize()
    await tg_app.start()
