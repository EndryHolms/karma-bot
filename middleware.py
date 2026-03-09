import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from firebase_db import get_user_language
from lexicon import get_text


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 3.0):
        self.rate_limit = rate_limit
        self.users_cache: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None

        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is not None:
            current_time = time.time()
            last_time = self.users_cache.get(user_id, 0.0)

            is_navigation = False
            if isinstance(event, CallbackQuery) and event.data:
                # Розширюємо список префіксів для навігаційних кнопок
                nav_prefixes = [
                    "menu:",
                    "change_zodiac",
                    "set_zodiac",
                    "set_lang",
                    "daily_card",
                    "love_reading",
                    "career_reading",
                    "universe_advice",
                ]
                is_navigation = any(event.data.startswith(prefix) for prefix in nav_prefixes)

            # Для навігаційних кнопок ставимо дуже маленький ліміт, для інших - стандартний
            limit = 0.5 if is_navigation else self.rate_limit

            if current_time - last_time < limit:
                if isinstance(event, CallbackQuery):
                    # Показуємо спливаюче вікно тільки якщо це НЕ навігація
                    if not is_navigation:
                        db = data.get("db")
                        # Мова за замовчуванням, якщо щось піде не так
                        lang = "uk" 
                        if db:
                            try:
                                lang = await get_user_language(db, user_id)
                            except Exception: # Якщо не вдалося швидко отримати мову, використовуємо дефолтну
                                pass
                        await event.answer(get_text(lang, "magic_wait"), show_alert=True)
                    else:
                        # Для навігації просто ігноруємо швидкі повторні натискання
                        await event.answer()
                return

            self.users_cache[user_id] = current_time

        return await handler(event, data)
