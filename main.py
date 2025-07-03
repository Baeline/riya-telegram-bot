# -------------------------------------------------------------
#  RIYA TELEGRAM BOT ✨  WITH GOOGLE SHEETS LOGGING + UPI FALLBACK
# -------------------------------------------------------------
#  • Logs chats + payments to Google Sheet
#  • 5 free messages → inline plan selector → UPI link
# -------------------------------------------------------------
import os, logging, json, hmac, hashlib, requests, asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, AIORateLimiter,
    CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import io

# ───────────────────────── ENV ───────────────────────────────
BOT_TOKEN         = os.getenv("BOT_TOKEN")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
ADMIN_USER_ID     = int(os.getenv("ADMIN_USER_ID", "0"))
SHEET_ID          = os.getenv("SHEET_ID")
SHEET_NAME        = os.getenv("SHEET_NAME", "Sheet1")
UPI_ID            = os.getenv("UPI_ID", "itsfashionbee-1@oksbi")

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

def log_to_sheet(user_id, user_msg, riya_reply, plan=None, payment_id=None):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, user_id, user_msg, riya_reply, plan or "", payment_id or ""]
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

# ──────────────────────── STATE │ MEMORY ─────────────────────
MSG_LIMIT = 5
paid_users = {}
message_counter = defaultdict(int)

PLANS = {
    "plan_49":  {"amount": 49,  "label": "💸 20 min – ₹49",   "duration": timedelta(minutes=20)},
    "plan_199": {"amount": 199, "label": "🔥 2 hr – ₹199",     "duration": timedelta(hours=2)},
    "plan_299": {"amount": 299, "label": "💖 15 chats – ₹299", "duration": timedelta(days=15)},
    "plan_999": {"amount": 999, "label": "👑 15 d unlimited – ₹999", "duration": timedelta(days=15)}
}

# ───────────────────── GPT RESPONSE ──────────────────────────
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
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Usage: /unlock <user_id> <plan_key>")
            return
        user_id = int(args[0])
        plan_key = args[1]
        if plan_key not in PLANS:
            await update.message.reply_text("❌ Invalid plan key.")
            return
        expire_at = datetime.utcnow() + PLANS[plan_key]["duration"]
        paid_users[user_id] = expire_at
        await update.message.reply_text(f"✅ Unlocked {user_id} for {plan_key}.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# ──────────────────────── UI MARKUPS ─────────────────────────
async def choose_plan_markup():
    buttons = [[InlineKeyboardButton(plan["label"], callback_data=key)] for key, plan in PLANS.items()]
    return InlineKeyboardMarkup(buttons)

# ──────────────────── Handlers ───────────────────────────────
async def start(update: Update, _):
    await update.message.reply_text("Heyy, I'm Riya 😘 – first 5 messages are free, then pick a plan!")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in paid_users and paid_users[user_id] and datetime.utcnow() > paid_users[user_id]:
        del paid_users[user_id]  # Expired

    if user_id not in paid_users:
        message_counter[user_id] += 1
        if message_counter[user_id] > MSG_LIMIT:
            await update.message.reply_text(
                "🚨 Free limit over! Choose a plan to keep talking:",
                reply_markup=await choose_plan_markup()
            )
            return

    reply = await gpt_reply(update.message.text)
    await update.message.reply_text(reply)
    log_to_sheet(user_id, update.message.text, reply)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    plan_key = query.data

    if plan_key not in PLANS:
        await query.message.reply_text("Plan not found, try again!")
        return

    plan = PLANS[plan_key]
    upi_msg = f"To unlock {plan['label']}, pay ₹{plan['amount']} to UPI ID:\n\n🧾 `{UPI_ID}`\n\nAfter payment, send screenshot to @baeline_support 🪄"
    await query.message.reply_text(upi_msg, parse_mode="Markdown")
    log_to_sheet(user_id, f"Clicked plan: {plan_key}", "", plan=plan_key)

# ──────────────────── Webhooks ───────────────────────────────
@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()

    # ✅ Initialize the bot for webhook-based updates
    if not tg_app.running:
        await tg_app.initialize()

    await tg_app.process_update(Update.de_json(data, tg_app.bot))
    return {"ok": True}


# ──────────────────── Launch ────────────────────────────────
async def setup():
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("unlock", unlock_command))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    tg_app.add_handler(CallbackQueryHandler(button_handler))
    
    await tg_app.initialize()
    await tg_app.start()

asyncio.get_event_loop().create_task(setup())
