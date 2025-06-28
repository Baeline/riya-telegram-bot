import asyncio

@app.on_event("startup")
async def startup():
    # Start Telegram bot non-blocking
    asyncio.create_task(telegram_app.initialize())
    asyncio.create_task(telegram_app.start())

@app.on_event("shutdown")
async def shutdown():
    await telegram_app.stop()
