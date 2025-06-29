import os
import logging
import random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# BOT TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN")  # or replace with your actual token string

# Profanity list
bad_words = [
    "nude", "boobs", "sex", "horny", "d***", "bitch", "suck", "f***",
    "pussy", "cock", "cum", "penis", "vagina", "asshole", "slut", "xxx"
]

# Tracking
user_strikes = {}
user_timeouts = {}

# START COMMAND
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hey {user.first_name} 😘 I'm Riya — smart, sassy, and sweet. But let’s set the vibe:\n\n"
        "💋 Keep it spicy, not sleazy\n"
        "🚫 No hate, no weird kinks\n"
        "⚠️ Three strikes and I go cold. Deal?"
    )

# MESSAGE HANDLER
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.lower()

    # If user is in timeout
    if user_id in user_timeouts and datetime.now() < user_timeouts[user_id]:
        await update.message.reply_text(
            "I told you once. You crossed the line. Come back in a few hours (or never 😌)."
        )
        return

    # Profanity check
    if any(word in text for word in bad_words):
        user_strikes[user_id] = user_strikes.get(user_id, 0) + 1

        if user_strikes[user_id] == 1:
            await update.message.reply_text("Uh oh 😬 That's strike 1. Keep it clean or I ghost you.")
        elif user_strikes[user_id] == 2:
            await update.message.reply_text("That’s strike 2, hotshot. One more and I vanish 💅")
        elif user_strikes[user_id] >= 3:
            user_timeouts[user_id] = datetime.now() + timedelta(hours=12)
            roast_lines = [
                "You want something hard? Try life, sweetie 😘",
                "Beta, I'm not your browser incognito mode.",
                "You sound like your phone is sticky. Ew.",
                "Next time talk to a mirror, not me 💋"
            ]
            await update.message.reply_text(
                f"{random.choice(roast_lines)}\n\nStrike 3. I’m out 🧊"
            )
        return

    # Normal response
    await update.message.reply_text("Hmm okay 👀 Tell me more...")

# MAIN FUNCTION
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == "__main__":
    main()
