import asyncio
import logging
import os

import google.generativeai as genai
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_settings
from firebase_db import init_firestore

# 👇 ВИПРАВЛЕНІ ІМПОРТИ (так надійніше)
from handlers.advice import router as advice_router
from handlers.payment import router as payment_router
from handlers.start import router as start_router
from handlers.tarot import router as tarot_router

# Переконайтеся, що створили файл prompts.py!
from prompts import KARMA_SYSTEM_PROMPT, UNIVERSE_ADVICE_SYSTEM_PROMPT


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

    genai.configure(api_key=settings.gemini_api_key)

    # Модель для Таро (містична)
    tarot_model = genai.GenerativeModel(
        model_name="gemini-2.0-flash", # Або "gemini-1.5-flash", перевірте назву
        system_instruction=KARMA_SYSTEM_PROMPT,
    )
    
    # Модель для Порад (філософська)
    advice_model = genai.GenerativeModel(
        model_name="gemini-2.0-flash", 
        system_instruction=UNIVERSE_ADVICE_SYSTEM_PROMPT,
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())
    
    # 👇 Dependency Injection: передаємо обидві моделі
    dp.workflow_data.update(db=db, tarot_model=tarot_model, advice_model=advice_model)

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
    asyncio.run(main())