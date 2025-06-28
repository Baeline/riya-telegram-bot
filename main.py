import os
import logging
from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.constants import ParseMode
import openai
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
bot = Bot(token=BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

# Create FastAPI app
app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Riya is online and spicy 😘"}

# Generate response from OpenAI
async def generate_reply(prompt: str) -> str:
    try:
        completion = await asyncio.to_thread(
            openai.ChatCompletion.create,
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You're Riya, a flirty, fun, Hinglish-speaking AI girlfriend. Mirror the user's vibe. Be sassy, sweet, and chaotic 💅."},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "Aww, Riya is confused right now 😵‍💫 Try again later?"

@app.post("/webhook")
async def process_webhook(req: Request):
    try:
        data = await req.json()
        update = Update.de_json(data, bot)

        if update.message and update.message.text:
            chat_id = update.message.chat.id
            user_text = update.message.text.strip()

            # Generate AI reply
            reply_text = await generate_reply(user_text)

            # Send message back
            await bot.send_message(
                chat_id=chat_id,
                text=reply_text,
                parse_mode=ParseMode.HTML
            )

        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": False, "error": str(e)}
