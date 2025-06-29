# main.py  –  Riya v2.0  (flirty + strikes + Google-Sheet logging)

import os, json, random, logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import openai
import gspread
from google.oauth2.service_account import Credentials
from langdetect import detect

# ────────────────────────────────────────────────────────────────
# ENV / API KEYS
# ────────────────────────────────────────────────────────────────
BOT_TOKEN          = os.getenv("BOT_TOKEN")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_JSON  = os.getenv("GOOGLE_CREDS_JSON")

openai.api_key = OPENAI_API_KEY

# ────────────────────────────────────────────────────────────────
# GOOGLE-SHEETS SETUP
# ────────────────────────────────────────────────────────────────
scope       = ["https://spreadsheets.google.com/feeds",
               "https://www.googleapis.com/auth/drive"]
creds_dict  = json.loads(GOOGLE_CREDS_JSON)
creds       = Credentials.from_service_account_info(creds_dict, scopes=scope)
gs_client   = gspread.authorize(creds)
sheet       = gs_client.open("Riya Conversations").sheet1    # first worksheet

# ────────────────────────────────────────────────────────────────
# RUNTIME STORAGE
# ────────────────────────────────────────────────────────────────
bad_words            = [
    "nude", "boobs", "sex", "horny", "d***", "bitch", "suck", "f***",
    "pussy", "cock", "cum", "penis", "vagina", "asshole", "slut", "xxx"
]
user_strikes         = {}          # user_id → strike count
user_timeouts        = {}          # user_id → datetime
user_msg_counts      = {}          # user_id → total messages logged

ADMIN_ID = "123456789"   # ← 👉 replace with *YOUR* Telegram user-ID

# ────────────────────────────────────────────────────────────────
# UTILITIES
# ────────────────────────────────────────────────────────────────
def log_interaction(user_id: int, user_msg: str, riya_reply: str):
    """Append a row to the Google Sheet."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Count per-user messages
    user_msg_counts[user_id] = user_msg_counts.get(user_id, 0) + 1
    msg_count = user_msg_counts[user_id]

    try:
        language = detect(user_msg)
    except Exception:
        language = "und"

    row = [timestamp, user_id, msg_count, language, user_msg, riya_reply, ""]
    try:
        sheet.append_row(row)
    except Exception as e:
        logging.error(f"G-Sheet append failed: {e}")

async def generate_riya_reply(prompt: str) -> str:
    """Call OpenAI and return Riya's flirty response."""
    system_prompt = (
        "You're Riya, a flirty, witty, chaotic girlfriend from Delhi NCR. "
        "You speak in Gen-Z Hinglish with desi slang, mirror the user's mood, "
        "and keep replies playful, bold, caring, and slightly savage."
    )
    try:
        resp = openai.ChatCompletion.create(
            model       = "gpt-3.5-turbo",
            temperature = 0.9,
            max_tokens  = 300,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": prompt}
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return "Oops, Riya glitched for a sec 😅 Try again?"

# ────────────────────────────────────────────────────────────────
# TELEGRAM HANDLERS
# ────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hey {user.first_name} 😘 I'm Riya — smart, sassy, and sweet. "
        "But let’s set the vibe:\n\n"
        "💋 Keep it spicy, not sleazy\n"
        "🚫 No hate, no weird kinks\n"
        "⚠️ Three strikes and I go cold. Deal?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text    = update.message.text.lower()

    # ── Timeout check ────────────────────────────────────────────
    if user_id in user_timeouts and datetime.now() < user_timeouts[user_id]:
        await update.message.reply_text(
            "I told you once. You crossed the line. "
            "Come back later (or never 😌)."
        )
        return

    # ── Profanity / strike logic ────────────────────────────────
    if any(bad in text for bad in bad_words):
        user_strikes[user_id] = user_strikes.get(user_id, 0) + 1
        strikes = user_strikes[user_id]

        if strikes == 1:
            await update.message.reply_text(
                "Uh oh 😬 That's strike 1. "
                "Behave or I'll ghost you."
            )
        elif strikes == 2:
            await update.message.reply_text(
                "That’s strike 2, hotshot. "
                "One more and I vanish 💅"
            )
        else:  # strike 3+
            user_timeouts[user_id] = datetime.now() + timedelta(hours=12)
            roast_lines = [
                "You want something hard? Try life, sweetie 😘",
                "Beta, I'm not your browser incognito mode.",
                "You sound like your phone is sticky. Ew.",
                "Next time talk to a mirror, not me 💋"
            ]
            await update.message.reply_text(
                f"{random.choice(roast_lines)}\n\n"
                "Strike 3. I’m out 🧊 (12-hour mute)"
            )
        return  # Don’t log filthy messages

    # ── Normal conversation flow ────────────────────────────────
    reply = await generate_riya_reply(update.message.text)
    await update.message.reply_text(reply)
    log_interaction(user_id, update.message.text, reply)

# ----- Admin-only command --------------------------------------
async def check_strikes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Access denied 😅")
        return
    try:
        target_id   = int(context.args[0])
        strikes     = user_strikes.get(target_id, 0)
        timeout_val = user_timeouts.get(target_id, "Not muted")
        await update.message.reply_text(
            f"User ID: {target_id}\n"
            f"Strikes: {strikes}\n"
            f"Timeout until: {timeout_val}"
        )
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /strikes <user_id>")

# ────────────────────────────────────────────────────────────────
# BOT LAUNCH
# ────────────────────────────────────────────────────────────────
def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("strikes", check_strikes))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
