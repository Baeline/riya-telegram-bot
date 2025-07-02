# ---------- Baeline / Riya Telegram Bot ----------
# Full, self-contained file: GPT chat + 5-msg limit + Razorpay Payment Link + Webhook unlock
# -------------------------------------------------
import os, logging, asyncio, hmac, hashlib, json, requests
from collections import defaultdict

from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import (
    Application, AIORateLimiter,
    CommandHandler, MessageHandler, filters
)
import openai

# ── ENVIRONMENT ───────────────────────────────────
BOT_TOKEN             = os.getenv("BOT_TOKEN")
OPENAI_API_KEY        = os.getenv("OPENAI_API_KEY")
RAZORPAY_KEY_ID       = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET   = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SIG  = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")  # optional

openai.api_key = OPENAI_API_KEY

# ── STATE (in-memory; swap with DB/Redis later) ──
message_count = defaultdict(int)   # {user_id: count}
paid_users    = set()              # {user_id}

# ── FASTAPI & PTB APP ─────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
app = FastAPI()

tg_app = (
    Application.builder()
    .token(BOT_TOKEN)
    .rate_limiter(AIORateLimiter())   # avoids Telegram 429s
    .concurrent_updates(True)
    .build()
)

# ── RAZORPAY HELPERS ─────────────────────────────
def create_payment_link(amount_rupees: int, user_id: int) -> str | None:
    """
    Creates a Razorpay *Payment Link* and returns the short_url.
    """
    url  = "https://api.razorpay.com/v1/payment_links"
    auth = (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)

    payload = {
        "amount"        : amount_rupees * 100,  # paise
        "currency"      : "INR",
        "description"   : f"Baeline access for Telegram user {user_id}",
        "customer"      : {"name": "Baeline User", "email": "noreply@baeline.com"},
        "notify"        : {"sms": False, "email": False},
        "callback_url"  : "https://baeline.com/unlock",   # optional
        "callback_method": "get",
        "notes"         : {"user_id": str(user_id)},
    }

    try:
        r = requests.post(url, auth=auth, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()["short_url"]
    except Exception as e:
        logging.error(f"Payment-link error: {e}")
        return None


def verify_razorpay_signature(body: bytes, header: str) -> bool:
    """
    Optional: Razorpay webhook signature verification.
    """
    if not RAZORPAY_WEBHOOK_SIG:
        return True  # skip if secret not set
    digest = hmac.new(RAZORPAY_WEBHOOK_SIG.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, header)


# ── BOT HANDLERS ─────────────────────────────────
async def start_cmd(update: Update, _ctx):
    await update.message.reply_text(
        "Heyy, I’m Riya 😘 — you get *5 free messages*. After that it’s ₹49 to keep the sparks flying!"
    )


async def chat_handler(update: Update, _ctx):
    user_id = update.effective_user.id

    # Already paid? skip limit
    if user_id not in paid_users:
        message_count[user_id] += 1

        if message_count[user_id] > 5:
            link = create_payment_link(49, user_id)
            if link:
                await update.message.reply_text(
                    "🛑 You’ve used your 5 free messages 💔\n\n"
                    f"💸 *Unlock full access now — just ₹49*\n"
                    f"[Tap to pay]({link})",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("Payment link error. Try again in a bit!")
            return  # block further chat until paid

    # ----- OpenAI chat -----
    prompt = update.message.text.strip()
    try:
        res = openai.ChatCompletion.create(
            model       = "gpt-3.5-turbo",
            temperature = 0.9,
            messages    = [
                {"role": "system", "content": "You’re Riya, an Indian flirty girlfriend. No chat history."},
                {"role": "user",   "content": prompt}
            ],
            max_tokens  = 256,
        )
        reply = res.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        reply = "Oops, server hiccup! Try again in a moment."

    await update.message.reply_text(reply)


tg_app.add_handler(CommandHandler("start", start_cmd))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

# ── WEBHOOK ENDPOINTS ────────────────────────────
@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    """
    Telegram pushes updates here.
    """
    data = await req.json()
    await tg_app.process_update(Update.de_json(data, tg_app.bot))
    return {"ok": True}


@app.post("/razorpay-webhook")
async def razorpay_webhook(req: Request):
    """
    Razorpay sends payment events here.
    """
    raw_body = await req.body()
    sig      = req.headers.get("x-razorpay-signature", "")

    # Signature check (optional but recommended)
    if not verify_razorpay_signature(raw_body, sig):
        logging.warning("⚠️  Invalid Razorpay signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = json.loads(raw_body)
    event   = payload.get("event")

    # We only care when the *payment link* is fully paid
    if event == "payment_link.paid":
        notes = payload["payload"]["payment_link"]["entity"]["notes"]
        user  = int(notes.get("user_id", 0))
        paid_users.add(user)
        logging.info(f"✅ Payment captured for user {user}")

    return {"status": "ok"}


# ── ENTRYPOINTS ──────────────────────────────────
if __name__ == "__main__":
    import sys, uvicorn, multiprocessing
    if len(sys.argv) > 1 and sys.argv[1] == "poll":
        tg_app.run_polling()
    else:
        workers = max(multiprocessing.cpu_count() // 2, 1)
        uvicorn.run("main:app", host="0.0.0.0", port=8000, workers=workers)
