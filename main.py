import asyncio
import logging

import google.generativeai as genai
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_settings
from firebase_db import init_firestore
from handlers import advice_router, payment_router, start_router, tarot_router
from prompts import KARMA_SYSTEM_PROMPT, UNIVERSE_ADVICE_SYSTEM_PROMPT


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = load_settings()

    db = await init_firestore(settings.firebase_cred_path)

    genai.configure(api_key=settings.gemini_api_key)

    tarot_model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview",
        system_instruction=KARMA_SYSTEM_PROMPT,
    )
    advice_model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview",
        system_instruction=UNIVERSE_ADVICE_SYSTEM_PROMPT,
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp.workflow_data.update(db=db, tarot_model=tarot_model, advice_model=advice_model)

    dp.include_router(payment_router)
    dp.include_router(start_router)
    dp.include_router(tarot_router)
    dp.include_router(advice_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
