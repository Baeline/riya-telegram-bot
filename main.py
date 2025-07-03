
import os, logging, hmac, hashlib, json, asyncio
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)
import openai

# ENVIRONMENT VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

# INIT SERVICES
app = FastAPI()
openai.api_key = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TELEGRAM APP
tg_app = Application.builder().token(BOT_TOKEN).build()
paid_users = set()
free_msg_counter = defaultdict(int)
payment_sessions = {}

# GPT GENERATION
async def generate_reply(prompt: str) -> str:
    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You're a sassy, flirty AI girlfriend named Riya 💋"},
                  {"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content

# HANDLERS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Heyy 👀 It's Riya baby! Let's chat 💖 First 5 messages free!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id in paid_users:
        pass
    elif free_msg_counter[user_id] < 5:
        free_msg_counter[user_id] += 1
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 Pay ₹49 to unlock", url="https://rzp.io/l/your-link-here")]
        ])
        await update.message.reply_text("Oops! Free limit over 😢 Tap below to unlock me 🔥", reply_markup=keyboard)
        return

    reply = await generate_reply(update.message.text)
    await update.message.reply_text(reply)

# CALLBACK (OPTIONAL)
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

# ROUTES
@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()
    await tg_app.process_update(Update.de_json(data, tg_app.bot))
    return {"ok": True}

@app.post("/razorpay/webhook")
async def razorpay_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    gen_sig = hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()

    if hmac.compare_digest(gen_sig, signature):
        payload = json.loads(body)
        if payload.get("event") == "payment.paid":
            payment_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id")
            logger.info(f"Payment success ✅ ID: {payment_id}")

            user_id = payment_sessions.get(payment_id)
            if user_id:
                paid_users.add(user_id)
                logger.info(f"User {user_id} unlocked 💎")
        return {"status": "ok"}
    else:
        raise HTTPException(status_code=400, detail="Invalid signature")

# SETUP
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
tg_app.add_handler(CallbackQueryHandler(button_callback))

# STARTUP (OPTIONAL)
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(tg_app.initialize())
