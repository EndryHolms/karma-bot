import asyncio
import logging
import os
import sys

# 👇 ВАЖЛИВО: Імпортуємо нову бібліотеку
from google import genai
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_settings
from firebase_db import init_firestore

# Імпорти роутерів
from handlers.advice import router as advice_router
from handlers.payment import router as payment_router
from handlers.start import router as start_router
from handlers.tarot import router as tarot_router


async def health_check(request: web.Request) -> web.Response:
    return web.Response(text="Bot is alive")


async def _run_web_server(port: int) -> None:
    app = web.Application()
    app.router.add_get("/", health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = load_settings()

    db = await init_firestore(settings.firebase_cred_path)

    # 👇 ГОЛОВНА ЗМІНА:
    # Замість genai.configure() ми створюємо Клієнта.
    # Цей клієнт вміє працювати з будь-якою моделлю (і Таро, і Поради).
    genai_client = genai.Client(api_key=settings.gemini_api_key)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())
    
    # 👇 ПЕРЕДАЄМО КЛІЄНТА В ХЕНДЛЕРИ
    # (Ми замінили tarot_model/advice_model на один genai_client)
    dp.workflow_data.update(db=db, genai_client=genai_client)

    dp.include_router(payment_router)
    dp.include_router(start_router)
    dp.include_router(tarot_router)
    dp.include_router(advice_router)

    port = int(os.environ.get("PORT", 8080))
    web_task = asyncio.create_task(_run_web_server(port))

    try:
        await dp.start_polling(bot)
    finally:
        web_task.cancel()
        await asyncio.gather(web_task, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)