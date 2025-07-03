# -------------------------------------------------------------
#  RIYA TELEGRAM BOT  ✨  FULLY AUTO‑UNLOCKING VERSION
# -------------------------------------------------------------
#  • FastAPI + python‑telegram‑bot v20.8 (async‑ready)
#  • 5 free messages → inline plan selector → Razorpay Payment Link
#  • Razorpay webhook → auto‑unlock user (no manual checks!)
#  • Plans:   49 ₹ / 20 min   ·   199 ₹ / 2 hr   ·   299 ₹ / 15 chats (15 d)
#               999 ₹ / 15 d unlimited
#  • GPT‑3.5‑Turbo brain (modify prompt to taste)
#  • In‑memory state (swap for Redis/DB later)
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

# ───────────────────────── ENV ───────────────────────────────
BOT_TOKEN               = os.getenv("BOT_TOKEN")
OPENAI_API_KEY          = os.getenv("OPENAI_API_KEY")
RAZORPAY_KEY_ID         = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET     = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")  # dashboard → secret

if not all([BOT_TOKEN, OPENAI_API_KEY, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET]):
    raise RuntimeError("❌ Missing one or more required env variables – check Railway settings.")

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
MSG_LIMIT        = 5                      # free msgs
paid_users       = {}  # {user_id: expire_datetime or None for unlimited}
message_counter  = defaultdict(int)  # {user_id: count}

# ──────────────────────── PLANS CONFIG ───────────────────────
PLANS = {
    "plan_49":  {"amount": 49,  "label": "💸 20 min – ₹49",  "duration": timedelta(minutes=20)},
    "plan_199": {"amount": 199, "label": "🔥 2 hr  – ₹199", "duration": timedelta(hours=2)},
    "plan_299": {"amount": 299, "label": "💞 15 chats – ₹299", "duration": timedelta(days=15)},
    "plan_999": {"amount": 999, "label": "👑 15 d unlimited – ₹999", "duration": timedelta(days=15)},
}

# ───────────────── Razorpay Payment Link Helper ──────────────
RZP_LINK_ENDPOINT = "https://api.razorpay.com/v1/payment_links"
SESSION_TIMEOUT   = 15  # seconds for HTTP

def create_payment_link(plan_key: str, user_id: int) -> str | None:
    plan = PLANS[plan_key]

    payload = {
        "amount": plan["amount"] * 100,  # paise
        "currency": "INR",
        "description": plan["label"],
        "customer": {
            "name": f"TG {user_id}",
            "email": "noreply@baeline.com"
        },
        "notify": {"sms": False, "email": False},
        "callback_url": "https://t.me/riyabaebot",  # after success hit bot link
        "callback_method": "get",
        "notes": {"user_id": str(user_id), "plan": plan_key},
    }
    try:
        resp = requests.post(
            RZP_LINK_ENDPOINT,
            auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
            json=payload,
            timeout=SESSION_TIMEOUT,
        )
        resp.raise_for_status()
        short_url = resp.json()["short_url"]
        log.info("🔗 Payment link created %s for user %s", short_url, user_id)
        return short_url
    except Exception as e:
        log.error("Razorpay link error: %s", e)
        return None

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
        return "Aww, server lag 😢 try again later!"

# ──────────────────── Telegram Handlers ──────────────────────
async def start(update: Update, _):
    await update.message.reply_text("Heyy, I'm Riya 😘 – first 5 messages are free, then pick a plan!")

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
        # Check expiry
        expiry = paid_users[user_id]
        if expiry and datetime.utcnow() > expiry:
            del paid_users[user_id]  # expired
        else:
            pass  # user still valid

    # If not paid
    if user_id not in paid_users:
        message_counter[user_id] += 1
        if message_counter[user_id] > MSG_LIMIT:
            await update.message.reply_text(
                "🛑 Free limit over! Choose a plan to keep talking:",
                reply_markup=await choose_plan_markup()
            )
            return

    # Generate GPT reply
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

    link = create_payment_link(plan_key, user_id)
    if link:
        await query.message.reply_text(
            f"Click to pay and come back ♥️ → {link}\n\nI'll auto‑unlock once Razorpay confirms!"
        )
    else:
        await query.message.reply_text("Failed to create payment link. Try again later!")

# ───────────────── Razorpay Webhook ─────────────────────────
@app.post("/razorpay/webhook")
async def razorpay_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    # Signature verification
    calc_sig = hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc_sig, signature):
        log.warning("⚠️ Invalid Razorpay signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = json.loads(body)
    event  = payload.get("event")

    if event == "payment_link.paid":
        entity = payload["payload"]["payment_link"]["entity"]
        user_note = entity["notes"].get("user_id")
        plan_key  = entity["notes"].get("plan")
        if user_note and plan_key in PLANS:
            user_id = int(user_note)
            duration = PLANS[plan_key]["duration"]
            expire_at = None if duration is None else datetime.utcnow() + duration
            paid_users[user_id] = expire_at
            log.info("🔓 Auto‑unlocked user %s for plan %s", user_id, plan_key)
    return {"status": "ok"}

# ───────────────── Telegram Webhook ─────────────────────────
# ───────────────── Telegram Webhook ─────────────────────────
@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}

# ───────────────── PTB Polling Fallback (Optional) ───────────
if __name__ == "__main__":
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    tg_app.add_handler(CallbackQueryHandler(button_handler))

    tg_app.run_polling()


