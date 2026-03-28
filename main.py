import asyncio
import logging
import os
import signal
import sys
from datetime import datetime

import google.generativeai as genai
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from google.generativeai.types import HarmBlockThreshold, HarmCategory
import pytz

from config import load_settings
from firebase_db import init_firestore
from handlers.admin import router as admin_router
from handlers.advice import router as advice_router
from handlers.payment import router as payment_router
from handlers.start import router as start_router
from handlers.tarot import router as tarot_router
from middleware import ChatLoggingMiddleware, ThrottlingMiddleware
from notifications import send_daily_horoscope, send_monthly_card_reminders
from prompts import KARMA_SYSTEM_PROMPT, UNIVERSE_ADVICE_SYSTEM_PROMPT

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}


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

def handle_exit(sig, frame):
    logging.warning(f"Received signal {sig}. Shutting down bot...")
    # Ми не виходимо тут примусово, дозволяємо asyncio завершити роботу

async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    settings = load_settings()
    db = await init_firestore(settings.firebase_cred_path)

    genai.configure(api_key=settings.gemini_api_key)

    model_name = settings.primary_model_name

    tarot_model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=KARMA_SYSTEM_PROMPT,
    )

    advice_model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=UNIVERSE_ADVICE_SYSTEM_PROMPT,
    )

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(ThrottlingMiddleware(rate_limit=3.0))
    dp.message.middleware(ChatLoggingMiddleware())

    dp.workflow_data.update(
        db=db,
        tarot_model=tarot_model,
        advice_model=advice_model,
        safety_settings=SAFETY_SETTINGS,
    )

    dp.include_router(admin_router)
    dp.include_router(payment_router)
    dp.include_router(start_router)
    dp.include_router(tarot_router)
    dp.include_router(advice_router)

    port = int(os.environ.get("PORT", 8080))
    web_task = asyncio.create_task(_run_web_server(port))

    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(send_monthly_card_reminders, trigger="cron", day=1, hour=12, minute=0, args=[bot, db])
    scheduler.add_job(send_daily_horoscope, trigger="cron", hour=9, minute=0, args=[bot, db, tarot_model])
    scheduler.start()

    # Catch-up: перевірка чи не пропущено гороскоп (якщо бот стартував після 09:00)
    tz = pytz.timezone("Europe/Kyiv")
    now = datetime.now(tz)
    if now.hour >= 9:
        logging.info("It's past 09:00 AM. Checking for missed daily horoscope...")
        asyncio.create_task(send_daily_horoscope(bot, db, tarot_model))

    # Реєстрація сигналів для логування
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, handle_exit)
        except Exception:
            pass

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