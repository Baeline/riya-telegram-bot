# -------------------------------------------------------------
#  RIYA TELEGRAM BOT  ✨  UPI-ONLY VERSION (No Razorpay)
# -------------------------------------------------------------
#  • 5 free messages → then show UPI ID & instructions
#  • Manual unlock via /unlock <user_id> <plan_key>
#  • UPI ID: itsfashionbee-1@oksbi
# -------------------------------------------------------------
import os, logging, asyncio
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, AIORateLimiter,
    CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import openai

# ───────────────────────── ENV ───────────────────────────────
BOT_TOKEN       = os.getenv("BOT_TOKEN")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
ADMIN_USER_ID   = int(os.getenv("ADMIN_USER_ID", "0"))

if not all([BOT_TOKEN, OPENAI_API_KEY]):
    raise RuntimeError("❌ Missing required env variables – check Railway.")

openai.api_key = OPENAI_API_KEY

# ──────────────────────── FASTAPI & PTB ──────────────────────
app = FastAPI()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("riya")

tg_app = (
    Application.builder()
    .token(BOT_TOKEN)
    .rate_limiter(AIORateLimiter())
    .concurrent_updates(True)
    .build()
)

# ──────────────────────── STATE │ In‑Memory ──────────────────
MSG_LIMIT        = 5
paid_users       = {}  # {user_id: expire_datetime or None for unlimited}
message_counter  = defaultdict(int)

# ──────────────────────── PLANS CONFIG ───────────────────────
PLANS = {
    "plan_49":  {"amount": 49,  "label": "💸 20\u00a0min – ₹49",  "duration": timedelta(minutes=20)},
    "plan_199": {"amount": 199, "label": "🔥 2\u00a0hr  – ₹199", "duration": timedelta(hours=2)},
    "plan_299": {"amount": 299, "label": "💖 15 chats – ₹299", "duration": timedelta(days=15)},
    "plan_999": {"amount": 999, "label": "👑 15\u00a0d unlimited – ₹999", "duration": timedelta(days=15)},
}

# ───────────────────── GPT Helper ────────────────────────────
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
        log.error("OpenAI error: %s", e)
        return "Aww, server lag 😭 try again later!"

# ──────────────── Admin Command: Manual Unlock ──────────────
async def unlock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: /unlock <user_id> <plan_key> <upi_ref? >
    Adds user to paid_users and optionally logs UPI ref‑ID to Google Sheet."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("🚫 Not allowed.")
        return

    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Usage: /unlock <user_id> <plan_key> [upi_ref]")
            return

        user_id  = int(args[0])
        plan_key = args[1]
        upi_ref  = args[2] if len(args) > 2 else "-"

        if plan_key not in PLANS:
            await update.message.reply_text("❌ Invalid plan key.")
            return

        # 1️⃣ Unlock in memory
        duration  = PLANS[plan_key]["duration"]
        expire_at = None if duration is None else datetime.utcnow() + duration
        paid_users[user_id] = expire_at

        # 2️⃣ Log to Google Sheet (if creds provided)
        try:
            if os.getenv("GSHEET_ID") and os.getenv("GSERVICE_JSON"):
                import gspread, json as _json
                sa = gspread.service_account_from_dict(_json.loads(os.getenv("GSERVICE_JSON")))
                sh = sa.open_by_key(os.getenv("GSHEET_ID"))
                ws = sh.sheet1  # first tab
                ws.append_row([
                    datetime.utcnow().isoformat(sep=" ", timespec="seconds"),
                    str(user_id),
                    plan_key,
                    upi_ref,
                    "Manual unlock"
                ])
        except Exception as e:
            log.error("GoogleSheet log error: %s", e)

        await update.message.reply_text(f"✅ Unlocked {user_id} for {plan_key}. Logged ref: {upi_ref}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

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

        duration = PLANS[plan_key]["duration"]
        expire_at = None if duration is None else datetime.utcnow() + duration
        paid_users[user_id] = expire_at
        await update.message.reply_text(f"✅ Unlocked {user_id} for {plan_key}.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# ──────────────────── Telegram Handlers ──────────────────────
async def start(update: Update, _):
    await update.message.reply_text("Heyy, I'm Riya 😘 – first 5 messages are free, then pay via UPI to continue 💖")

async def choose_plan_markup():
    buttons = [
        [InlineKeyboardButton(plan["label"], callback_data=key)]
        for key, plan in PLANS.items()
    ]
    return InlineKeyboardMarkup(buttons)

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Check paid status
    if user_id in paid_users:
        expiry = paid_users[user_id]
        if expiry and datetime.utcnow() > expiry:
            del paid_users[user_id]

    if user_id not in paid_users:
        message_counter[user_id] += 1
        if message_counter[user_id] > MSG_LIMIT:
            await update.message.reply_text(
                "🚫 Free limit over! Choose a plan and pay via UPI:",
                reply_markup=await choose_plan_markup()
            )
            return

    reply = await gpt_reply(update.message.text)
    await update.message.reply_text(reply)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_key = query.data
    user_id = query.from_user.id

    if plan_key not in PLANS:
        await query.message.reply_text("Plan not found, try again!")
        return

    plan = PLANS[plan_key]
    await query.message.reply_text(
        f"💳 Pay ₹{plan['amount']} to *itsfashionbee-1@oksbi* via UPI 📲\nThen send your payment ID or screenshot here!\n\nOnce verified, I'll unlock you 💕",
        parse_mode="Markdown"
    )

# ───────────────── Telegram Webhook ─────────────────────────
@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()
    await tg_app.process_update(Update.de_json(data, tg_app.bot))
    return {"ok": True}

# ────────────────────────── Launch ───────────────────────────
# ────────────────────────── Launch ───────────────────────────
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("unlock", unlock_command))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    tg_app.add_handler(CallbackQueryHandler(button_handler))

    await tg_app.initialize()
    await tg_app.start()
    yield
    await tg_app.stop()
    await tg_app.shutdown()

app.router.lifespan_context = lifespan
