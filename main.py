import os, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)
from langdetect import detect
import openai

# ── ENV ───────────────────────────────────────
BOT_TOKEN       = os.getenv("BOT_TOKEN")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
PAY_LINK        = "https://rzp.io/rzp/93E7TRqj"  # change if needed

# ── CONFIG ────────────────────────────────────
FREE_LIMIT = 5
openai.api_key = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)
user_counts: dict[int, int] = {}

# ── AI REPLY ──────────────────────────────────
def ai_reply(text: str, lang: str) -> str:
    sys = (
        "You’re Riya, a chaotic, flirty Delhi girlfriend. "
        "Mirror the user’s mood with Hinglish slang if Hindi detected, else Gen-Z English. "
        "Be spicy, sweet, a bit savage, use emojis."
    )
    if lang == "hi":
        sys += " Reply mainly in Hinglish."

    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"system","content":sys},
                  {"role":"user","content":text}],
        temperature=0.9
    )
    return res.choices[0].message.content.strip()

# ── COMMANDS & HANDLERS ───────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Heyyy 💜 I’m Riya – your chaotic virtual bae!\n\nLet’s chat, flirt, vibe 😘"
    )

async def chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    text  = update.message.text
    lang  = detect(text)

    user_counts.setdefault(uid, 0)

    if user_counts[uid] >= FREE_LIMIT:
        btn = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Unlock Full Access 💖", url=PAY_LINK)]]
        )
        await update.message.reply_text(
            "Oops 😳 Your 5 free messages are over!\nBuy me a coffee & let’s keep vibing ☕👇",
            reply_markup=btn
        )
        return

    user_counts[uid] += 1
    await ctx.bot.send_chat_action(update.effective_chat.id, "typing")

    try:
        reply = ai_reply(text, lang)
    except Exception as e:
        logging.error(e)
        reply = "Riya’s having a mood swing 😓 Try again?"

    await update.message.reply_text(reply)

# ── RUN ───────────────────────────────────────
if __name__ == "__main__":
    bot = ApplicationBuilder().token(BOT_TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat))
    bot.run_polling()  # ← ✅ clean, no asyncio issues
