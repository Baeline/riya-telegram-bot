# -------------------------------------------------------------
# Riya Telegram Bot – ONE‑FILE, PRODUCTION‑READY, ERROR‑PROOF 💖
# -------------------------------------------------------------
# Features
#   • FastAPI + python‑telegram‑bot v20.8 (async)
#   • /start + chat handler (GPT‑powered)
#   • 5‑message free limit → Razorpay Payment Link (₹49)
#   • Razorpay webhook to unlock paid users
#   • AIORateLimiter to avoid Telegram 429s
#   • Works via Webhook (Railway) or Polling (local)
# -------------------------------------------------------------

import os, logging, hmac, hashlib, json, requests, asyncio
from collections import defaultdict
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import (
    Application, AIORateLimiter,
    CommandHandler, MessageHandler, filters
)
import openai

# ──────────────────── ENV VARIABLES ──────────────────────────
BOT_TOKEN               = os.getenv("BOT_TOKEN")                 # Telegram bot token
OPENAI_API_KEY          = os.getenv("OPENAI_API_KEY")            # OpenAI key (sk‑...)
RAZORPAY_KEY_ID         = os.getenv("RAZORPAY_KEY_ID")           # Razorpay creds
RAZORPAY_KEY_SECRET     = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")  # optional

if not all([BOT_TOKEN, OPENAI_API_KEY, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET]):
    raise RuntimeError("❌ Missing one or more required environment variables.")

openai.api_key = OPENAI_API_KEY

# ──────────────────── STATE (in‑memory) ──────────────────────
MSG_LIMIT    = 5                                     # free messages per user
PAID_AMOUNT  = 49                                    # ₹
message_cnt: defaultdict[int, int] = defaultdict(int)
paid_users: set[int] = set()

# ──────────────────── LOGGING ────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("riya")

# ──────────────────── FASTAPI & TELEGRAM APP ─────────────────
app = FastAPI()

tg_app = (
    Application.builder()
    .token(BOT_TOKEN)
    .rate_limiter(AIORateLimiter())
    .concurrent_updates(True)   # handle multiple updates in parallel
    .build()
)

# ──────────────────── RAZORPAY HELPERS ───────────────────────

def create_payment_link(amount_rupees: int, user_id: int) -> Optional[str]:
    """Generate a Razorpay Payment Link & return short_url."""
    url  = "https://api.razorpay.com/v1/payment_links"
    auth = (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    payload = {
        "amount": amount_rupees * 100,
        "currency": "INR",
        "description": f"Baeline access for Telegram user {user_id}",
        "customer": {"name": "Baeline User", "email": "noreply@baeline.com"},
        "notify": {"sms": False, "email": False},
        "callback_url": "https://baeline.com/unlock",
        "callback_method": "get",
        "notes": {"user_id": str(user_id)},
    }
    try:
        r = requests.post(url, json=payload, auth=auth, timeout=10)
        r.raise_for_status()
        short_url = r.json()["short_url"]
        log.info("🔗 Created payment link %s for user %s", short_url, user_id)
        return short_url
    except Exception as exc:
        log.error("Razorpay link error: %s", exc)
        return None


def verify_rzp_signature(body: bytes, header: str) -> bool:
    """Verify Razorpay webhook signature (if secret set)"""
    if not RAZORPAY_WEBHOOK_SECRET:
        return True
    digest = hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, header)

# ──────────────────── BOT HANDLERS ───────────────────────────
async def start_cmd(update: Update, _ctx):
    await update.message.reply_text(
        "Heyy, I’m Riya 😘\nYou get *5 free messages*. After that it’s just ₹49 to keep chatting!",
        parse_mode="Markdown",
    )


async def chat_handler(update: Update, _ctx):
    user_id = update.effective_user.id
    user_msg = update.message.text.strip()

    # ── Check payment / free‑msg limit ──
    if user_id not in paid_users:
        message_cnt[user_id] += 1
        if message_cnt[user_id] > MSG_LIMIT:
            link = create_payment_link(PAID_AMOUNT, user_id)
            if link:
                await update.message.reply_text(
                    "🛑 You’ve used your *5 free messages* 💔\n\n" +
                    f"💸 *Unlock full access – ₹{PAID_AMOUNT}*\n[Tap to pay]({link})",
                    parse_mode="Markdown",
                )
            else:
                await update.message.reply_text("Payment link error. Try again later!")
            return  # stop further processing

    # ── Generate GPT reply ──
    try:
        res = await asyncio.to_thread(
            openai.ChatCompletion.create,
            model="gpt-3.5-turbo",
            temperature=0.9,
            max_tokens=256,
            messages=[
                {"role": "system", "content": "You’re Riya, an Indian flirty girlfriend. No history."},
                {"role": "user", "content": user_msg},
            ],
        )
        reply = res.choices[0].message.content.strip()
    except Exception as exc:
        log.error("OpenAI error: %s", exc)
        reply = "Oops, server hiccup! Try again in a bit 😅"

    await update.message.reply_text(reply)


tg_app.add_handler(CommandHandler("start", start_cmd))

tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

# ──────────────────── FASTAPI ENDPOINTS ──────────────────────
@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()
    await tg_app.process_update(Update.de_json(data, tg_app.bot))
    return {"ok": True}



@app.post("/razorpay-webhook")
async def razorpay_webhook(req: Request):
    """Handle Razorpay payment_link.paid webhook."""
    raw_body = await req.body()
    signature = req.headers.get("x-razorpay-signature", "")

    if not verify_rzp_signature(raw_body, signature):
        log.warning("⚠️ Invalid Razorpay signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = json.loads(raw_body)
    if payload.get("event") == "payment_link.paid":
        user_note = payload["payload"]["payment_link"]["entity"]["notes"].get("user_id")
        if user_note and user_note.isdigit():
            paid_users.add(int(user_note))
            log.info("✅ Payment captured for user %s", user_note)
    return {"status": "ok"}

# ──────────────────── ENTRYPOINTS ────────────────────────────
if __name__ == "__main__":
    import sys, uvicorn, multiprocessing

    if len(sys.argv) > 1 and sys.argv[1] == "poll":
        # Local polling mode → python main.py poll
        log.info("🔄 Running in polling mode…")
        tg_app.run_polling()
    else:
        # Webhook / production mode (Railway) → python main.py
        workers = max(multiprocessing.cpu_count() // 2, 1)
        log.info("🚀 Launching Uvicorn with %s worker(s)…", workers)
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8000)),
            workers=workers,
        )
