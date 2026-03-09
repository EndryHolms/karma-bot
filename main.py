import asyncio
import logging
import os
import sys

# Використовуємо перевірену бібліотеку
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
    """Розумна обгортка, яка динамічно встановлює system_instruction"""

    def __init__(self, primary_name: str, fallback_name: str):
        self.primary_name = primary_name
        self.fallback_name = fallback_name
        # Створюємо базові моделі без інструкцій, щоб не створювати їх на кожен запит
        self.primary_base = genai.GenerativeModel(primary_name)
        self.fallback_base = genai.GenerativeModel(fallback_name)

    def generate_content(self, contents, system_instruction: str | None = None, **kwargs):
        # Якщо передано інструкцію, створюємо нову модель "на льоту"
        # Це офіційний спосіб задати системну інструкцію в google-generativeai > 0.5.0
        primary_model = (
            genai.GenerativeModel(
                self.primary_name, system_instruction=system_instruction
            )
            if system_instruction
            else self.primary_base
        )
        fallback_model = (
            genai.GenerativeModel(
                self.fallback_name, system_instruction=system_instruction
            )
            if system_instruction
            else self.fallback_base
        )

        try:
            # Спроба №1: Основна модель
            return primary_model.generate_content(contents, **kwargs)
        except Exception as e:
            logging.warning(
                f"⚠️ Основна модель впала ({e}). Перемикаюсь на запасну: {fallback_model.model_name}"
            )
            # Спроба №2: Запасна модель
            return fallback_model.generate_content(contents, **kwargs)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = load_settings()

    # Ініціалізація бази даних
    db = await init_firestore(settings.firebase_cred_path)

    # КОНФІГУРАЦІЯ GEMINI
    genai.configure(api_key=settings.gemini_api_key)

    # Ініціалізуємо моделі без системних промптів.
    # Промпт буде додаватись динамічно в хендлерах.
    tarot_model = SafeGeminiModel(
        primary_name=settings.primary_model_name,
        fallback_name=settings.fallback_model_name,
    )

    advice_model = SafeGeminiModel(
        primary_name=settings.primary_model_name,
        fallback_name=settings.fallback_model_name,
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Вмикаємо ліміт 3 секунди на текстові повідомлення та кліки по кнопках
    dp.message.middleware(ThrottlingMiddleware(rate_limit=3.0))
    dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=3.0))

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

    # ДОДАЄМО ПЛАНУВАЛЬНИК
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    # Налаштовуємо запуск щодня о 12:00 (за Києвом)
    scheduler.add_job(
        send_daily_reminders, trigger="cron", hour=12, minute=0, args=[bot, db]
    )
    # НОВА ЗАДАЧА: Ранковий іронічний гороскоп (о 09:00 щодня)
    scheduler.add_job(
        send_daily_horoscope,
        trigger="cron",
        hour=9,
        minute=0,
        args=[bot, db, tarot_model],
    )
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
