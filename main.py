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
import openai

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tokens
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Bad words list
bad_words = [
    "nude", "boobs", "sex", "horny", "d***", "bitch", "suck", "f***",
    "pussy", "cock", "cum", "penis", "vagina", "asshole", "slut", "xxx"
]

# User tracking
user_strikes = {}
user_timeouts = {}

# Start message
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hey {user.first_name} 😘 I'm Riya — smart, sassy, and sweet. But let’s set the vibe:\n\n"
        "💋 Keep it spicy, not sleazy\n"
        "🚫 No hate, no weird kinks\n"
        "⚠️ Three strikes and I go cold. Deal?"
    )

# Generate GPT-based reply
async def generate_reply(prompt: str) -> str:
    system_prompt = (
        "You're Riya, a flirty, witty, chaotic girlfriend from Delhi NCR. "
        "You speak in Gen Z Hinglish, use desi slang, and mirror the user's mood. "
        "You're bold, caring, and spicy with attitude — full girlfriend experience."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "Oops, Riya glitched for a sec 😅 Try again?"

# Handle incoming messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.lower()

    # Timeout check
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

    # Otherwise, respond normally
    reply = await generate_reply(update.message.text)
    await update.message.reply_text(reply)

# Start the bot
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
