import os
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web
import asyncio

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8010))
WEBHOOK_URL = "https://riya-production.up.railway.app/webhook"

bot = Bot(BOT_TOKEN)
application = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey boo 😘 Riya is online!")

application.add_handler(CommandHandler("start", start))

async def webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, bot)
        await application.update_queue.put(update)
        return web.Response(text="ok", status=200)
    except Exception as e:
        print("Webhook error:", e)
        return web.Response(text="webhook fail", status=500)

async def main():
    await application.initialize()
    await bot.set_webhook(url=WEBHOOK_URL)

    app = web.Application()
    app.router.add_post("/webhook", webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"✅ Riya is live on port {PORT}")
    await application.start()

asyncio.run(main())
