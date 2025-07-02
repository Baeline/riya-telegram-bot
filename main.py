
import os, json, hmac, csv, hashlib, logging, asyncio
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI
from langdetect import detect

# Google Sheets integration
import gspread
from google.oauth2.service_account import Credentials

# ---------- ENV ----------
BOT_TOKEN  = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
RZP_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

openai = OpenAI(api_key=OPENAI_KEY)

# ---------- SHEET AUTH ----------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_JSON_PATH = "service_account.json"

creds = Credentials.from_service_account_file(SERVICE_JSON_PATH, scopes=SCOPES)
gclient = gspread.authorize(creds)
sheet = gclient.open_by_key(GOOGLE_SHEET_ID).sheet1

# ---------- LOGGING ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_conversation(user_id: int, user_msg: str, riya_reply: str):
    try:
        sheet.append_row([
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            user_id,
            user_sessions[user_id]["count"],
            detect(user_msg),
            user_msg,
            riya_reply,
            ""
        ])
    except Exception as e:
        logger.warning(f"Google Sheets logging failed: {e}")

# ---------- STATE ----------
user_sessions = {}
PAY_LINK = "https://rzp.io/rzp/93E7TRqj"

# ---------- TELEGRAM ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey cutie 😘 I'm Riya — Delhi's sassiest virtual bae.
"
        "You get *5 free messages* to win me over. Ready?",
        parse_mode=constants.ParseMode.MARKDOWN
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    session = user_sessions.setdefault(user_id, {"count": 0, "paid": False})

    if session["paid"]:
        reply = await generate_reply(text)
        await update.message.reply_text(reply)
        log_conversation(user_id, text, reply)
        return

    if session["count"] < 5:
        session["count"] += 1
        reply = await generate_reply(text)
        await update.message.reply_text(reply)
        log_conversation(user_id, text, reply)
    else:
        await update.message.reply_text(
            "Oops! Your *5 free messages* are done 😢
"
            "Unlock unlimited flirting for just ₹49",
            parse_mode=constants.ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 Unlock Full Chat – ₹49", url=PAY_LINK)]
            ])
        )

async def generate_reply(user_text: str) -> str:
    lang = detect(user_text)
    system_prompt = (
        "You are Riya, a 23‑year‑old Delhi girl. You're flirty, playful, and roast the user lovingly. "
        "Always sprinkle Hinglish slang (yaar, babu, oye) and Gen‑Z emojis 🫶😏."
    )
    if lang == "hi":
        system_prompt += " Reply mainly in Hinglish with desi flavour."
    else:
        system_prompt += " Reply in spicy Gen‑Z English."

    completion = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        temperature=0.9
    )
    return completion.choices[0].message.content.strip()

# ---------- RAZORPAY ----------
app = FastAPI()

@app.post("/razorpay/webhook")
async def razorpay_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    expected = hmac.new(
        RZP_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = await request.json()
    if payload.get("event") == "payment.captured":
        entity = payload["payload"]["payment"]["entity"]
        ref_id = entity.get("reference_id", "")
        if ref_id.startswith("tg_"):
            user_id = int(ref_id.replace("tg_", ""))
            user_sessions.setdefault(user_id, {"count": 5, "paid": False})
            user_sessions[user_id]["paid"] = True
            await bot_send_message(user_id, "Payment received ✅ — I'm all yours now, babu! 😘")
    return {"status": "ok"}

async def bot_send_message(chat_id: int, text: str):
    await app_context.bot.send_message(chat_id=chat_id, text=text)

# ---------- START BOT ----------
@app.on_event("startup")
async def startup():
    global app_context
    tg_app = ApplicationBuilder().token(BOT_TOKEN).build()
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_context = tg_app
    asyncio.create_task(tg_app.run_polling())
