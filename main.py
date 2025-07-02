import os, logging, json, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from langdetect import detect
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ENV VARS
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
FREE_LIMIT = int(os.getenv("FREE_LIMIT", 5))

openai.api_key = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)
user_sessions = {}
paid_users = set()

# ✅ Google Sheet Logging
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS_JSON), scope)
client = gspread.authorize(creds)
sheet = client.open("Riya Conversations").sheet1

def log_to_sheet(user_id, user_message, reply):
    try:
        sheet.append_row([str(user_id), user_message, reply])
    except Exception as e:
        logging.error(f"Sheet log failed: {e}")

# ✅ Razorpay Order API Logic
def create_order(user_id):
    url = "https://api.razorpay.com/v1/orders"
    data = {
        "amount": 4900,
        "currency": "INR",
        "receipt": f"tg_{user_id}",
        "payment_capture": 1
    }
    response = requests.post(
        url,
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
        json=data
    )
    return response.json()

def verify_payment(user_id):
    url = "https://api.razorpay.com/v1/payments"
    response = requests.get(
        url,
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )
    if response.status_code == 200:
        data = response.json()
        for payment in data.get("items", []):
            if payment["status"] == "captured" and f"tg_{user_id}" in str(payment.get("notes", {})):
                return True
    return False

# ✅ AI Response
async def generate_reply(message, language):
    system_prompt = "You're Riya, a flirty, emotional AI girlfriend. Respond with sass and sweetness."
    if language == "hi":
        system_prompt += " Speak in Hinglish with desi swag and emojis 💕"
    else:
        system_prompt += " Use Gen Z tone, flirt, tease, and keep it spicy 😘"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
    )
    return response.choices[0].message.content.strip()

# ✅ Payment Prompt
async def send_payment_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    order = create_order(user_id)
    order_id = order.get("id")
   payment_url = f"https://baeline.com/pay?order_id={order_id}" if order_id else "https://baeline.com/pay"


    keyboard = [
        [InlineKeyboardButton("💸 Unlock Full Access – ₹49", url=payment_url)],
        [InlineKeyboardButton("✅ I already paid", callback_data="verify_payment")]
    ]
    await update.message.reply_text(
        "You’ve used up your 5 free messages 💔\n\nWanna keep chatting with me? 😉",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ✅ Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Heyy, I'm Riya 💋\nType anything to start chatting!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions.setdefault(user_id, {"count": 0})

    if user_id in paid_users:
        pass
    elif user_sessions[user_id]["count"] >= FREE_LIMIT:
        await send_payment_prompt(update, context)
        return
    else:
        user_sessions[user_id]["count"] += 1

    user_message = update.message.text
    language = detect(user_message)
    reply = await generate_reply(user_message, language)
    await update.message.reply_text(reply)
    log_to_sheet(user_id, user_message, reply)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "verify_payment":
        if verify_payment(user_id):
            paid_users.add(user_id)
            await query.edit_message_text("✅ Payment confirmed! Let’s continue 💕")
        else:
            await query.edit_message_text("❌ No payment found yet. Try again after a min!")

# ✅ Run Bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
