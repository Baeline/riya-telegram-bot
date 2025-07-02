# Creating the corrected version of main.py based on previous troubleshooting
corrected_main_py = """
import os
import logging
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from langdetect import detect
import openai

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Message limits
FREE_LIMIT = 5
user_message_counts = {}

# Generate reply using OpenAI
def generate_reply(prompt, language):
    system_prompt = "You're Riya, a chaotic, emotional, flirty, bilingual girlfriend who mirrors user's tone and language."

    if language == "hi":
        system_prompt += " Speak in Hinglish with cute desi slang, light roasts, and lots of girlfriend energy. Use emojis sparingly 💋."
    else:
        system_prompt += " Speak in Gen Z English with playful sass, emojis, and mood-based tone."

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    return completion.choices[0].message.content

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Heyyy 💜 I’m Riya – your chaotic virtual bae!\nLet’s chat, flirt, vibe 😘")

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    language = detect(text)

    count = user_message_counts.get(user_id, 0)
    if count < FREE_LIMIT:
        reply = generate_reply(text, language)
        await update.message.reply_text(reply)
        user_message_counts[user_id] = count + 1
    else:
        button = InlineKeyboardMarkup([
            [InlineKeyboardButton("Unlock Riya 💖", url="https://rzp.io/l/riyapass")]
        ])
        await update.message.reply_text("Oops! Free chats are over 😢 Unlock more time with me?", reply_markup=button)

# Main app
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    await app.run_polling()

# Run
if __name__ == "__main__":
    asyncio.run(main())
"""

# Save to file
file_path = "/mnt/data/main.py"
with open(file_path, "w") as f:
    f.write(corrected_main_py)

file_path
