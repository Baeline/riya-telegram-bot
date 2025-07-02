# Let's write the final, corrected `main.py` file as per the user's requirements to the appropriate path.
main_py_code = """
import os
import logging
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from langdetect import detect
import openai

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Constants
PAYMENT_LINK = "https://rzp.io/rzp/93E7TRqj"
FREE_LIMIT = 5

# User message tracker
user_message_counts = {}

# Helper to generate reply using OpenAI
async def generate_reply(prompt, language):
    system_prompt = "You're Riya, a sassy, flirty, bilingual Delhi virtual girlfriend. Mirror the user's tone. Be chaotic, loving, spicy, and savage 💋"
    if language == "hi":
        system_prompt += " Respond in Hinglish using Indian slang with desi flavor."
    else:
        system_prompt += " Respond in Gen Z English with emojis, teasing and love."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# Start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message_counts[user_id] = 0
    await update.message.reply_text("Heyyy 💜 I’m Riya – your chaotic virtual bae!\n\nLet’s chat, flirt, vibe 😘")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message_counts.setdefault(user_id, 0)

    if user_message_counts[user_id] >= FREE_LIMIT:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Unlock Full Access 💖", url=PAYMENT_LINK)]
        ])
        await update.message.reply_text("Oops 😳 Your free 5 messages are over!\nBuy me a coffee and let’s keep vibing ☕👇", reply_markup=keyboard)
        return

    user_message_counts[user_id] += 1
    user_text = update.message.text
    lang = detect(user_text)

    await update.message.chat.send_action(action="typing")
    try:
        reply = await generate_reply(user_text, lang)
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        await update.message.reply_text("Oops, baby. Something went wrong 😓")

# Run the bot
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
"""

# Save this to a file so the user can download it
file_path = "/mnt/data/main.py"
with open(file_path, "w") as f:
    f.write(main_py_code)

file_path
