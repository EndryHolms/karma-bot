import asyncio
import logging
import os
import sys


# 👇 Використовуємо перевірену бібліотеку
import google.generativeai as genai
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_settings
from firebase_db import init_firestore
from middleware import ThrottlingMiddleware

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from notifications import send_daily_reminders, send_daily_horoscope

# Імпорти роутерів
from handlers.advice import router as advice_router
from handlers.payment import router as payment_router
from handlers.start import router as start_router
from handlers.tarot import router as tarot_router

# Імпортуємо системні промпти
from prompts import KARMA_SYSTEM_PROMPT, UNIVERSE_ADVICE_SYSTEM_PROMPT


async def health_check(request: web.Request) -> web.Response:
    """Відповідає 'Bot is alive' для UptimeRobot"""
    return web.Response(text="Bot is alive")


async def _run_web_server(port: int) -> None:
    """Запускає веб-сервер на потрібному порті"""
    app = web.Application()
    app.router.add_get("/", health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    # Тримаємо сервер запущеним
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()

class SafeGeminiModel:
    """Розумна обгортка, яка автоматично перемикає моделі при помилці"""
    def __init__(self, primary_name: str, fallback_name: str, system_instruction: str = None):
        # Ініціалізуємо одразу дві моделі з однаковими налаштуваннями
        kwargs = {"system_instruction": system_instruction} if system_instruction else {}
        self.primary = genai.GenerativeModel(primary_name, **kwargs)
        self.fallback = genai.GenerativeModel(fallback_name, **kwargs)

    def generate_content(self, contents, **kwargs):
        try:
            # Спроба №1: Основна модель (flash)
            return self.primary.generate_content(contents, **kwargs)
        except Exception as e:
            import logging
            logging.warning(f"⚠️ Основна модель впала ({e}). Перемикаюсь на запасну: {self.fallback.model_name}")
            # Спроба №2: Запасна модель (pro)
            return self.fallback.generate_content(contents, **kwargs)

async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = load_settings()

    # Ініціалізація бази даних
    db = await init_firestore(settings.firebase_cred_path)

    # 👇 КОНФІГУРАЦІЯ GEMINI
    genai.configure(api_key=settings.gemini_api_key)

    # 👇 ВАЖЛИВА ЗМІНА:
    # Використовуємо "gemini-1.5-flash" замість "2.5-lite".
    # Причина: у 2.5 ліміт 20 запитів/день, а тут - 1500.
    # Ініціалізуємо стандартні моделі без підстраховки
    tarot_model = genai.GenerativeModel(
        "gemini-3.1-flash-lite-preview",
        system_instruction=KARMA_SYSTEM_PROMPT
    )

    advice_model = genai.GenerativeModel(
        "gemini-3.1-flash-lite-preview",
        system_instruction=UNIVERSE_ADVICE_SYSTEM_PROMPT
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    # 👇 ДОДАЙ ЦІ ДВА РЯДКИ:
    # Вмикаємо ліміт 3 секунди на текстові повідомлення та кліки по кнопках
    dp.message.middleware(ThrottlingMiddleware(rate_limit=3.0))
    dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=3.0))

    # Передаємо моделі в хендлери
    dp.workflow_data.update(db=db, tarot_model=tarot_model, advice_model=advice_model)
    # ... далі код йде без змін ...
    
    # Передаємо моделі в хендлери
    dp.workflow_data.update(db=db, tarot_model=tarot_model, advice_model=advice_model)

    dp.include_router(payment_router)
    dp.include_router(start_router)
    dp.include_router(tarot_router)
    dp.include_router(advice_router)

    # Запуск веб-сервера для UptimeRobot
    port = int(os.environ.get("PORT", 8080))
    # Запускаємо сервер в фоні (task), щоб не блокувати бота
    web_task = asyncio.create_task(_run_web_server(port))
    logging.info(f"🌍 Web server started on port {port}")

    # 👇 ДОДАЄМО ПЛАНУВАЛЬНИК 👇
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    # Налаштовуємо запуск щодня о 12:00 (за Києвом)
    scheduler.add_job(send_daily_reminders, trigger='cron', hour=12, minute=0, args=[bot, db])
    # НОВА ЗАДАЧА: Ранковий іронічний гороскоп (о 09:00 щодня)
    scheduler.add_job(send_daily_horoscope, trigger='cron', hour=9, minute=0, args=[bot, db, tarot_model])
    scheduler.start()
    logging.info("⏰ Планувальник завдань запущено.")

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