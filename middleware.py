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
        
        # Визначаємо ID користувача
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
            
        if user_id is not None:
            current_time = time.time()
            last_time = self.users_cache.get(user_id, 0.0)
            
            # 👇 МАГІЯ: Визначаємо, чи це "легка" кнопка меню
            is_fast_button = False
            if isinstance(event, CallbackQuery) and event.data:
                # Список кнопок, які мають працювати МИТТЄВО
                fast_callbacks = [
                    "menu:profile", "menu:back", "change_zodiac", 
                    "set_zodiac", "set_lang", "topup:"
                ]
                is_fast_button = any(event.data.startswith(prefix) for prefix in fast_callbacks)
            
            # Встановлюємо ліміт: 0.3с для меню, 3.0с для магії
            limit = 0.3 if is_fast_button else self.rate_limit
            
            if current_time - last_time < limit:
                if isinstance(event, CallbackQuery):
                    # Показуємо вікно ТІЛЬКИ для важких запитів (не для меню)
                    if not is_fast_button:
                        db = data.get("db")
                        lang = await get_user_language(db, user_id) if db else "uk"
                        await event.answer(get_text(lang, "magic_wait"), show_alert=True)
                    else:
                        # Для меню просто мовчки ігноруємо занадто швидкий повторний клік
                        await event.answer()
                return 
            
            # Оновлюємо час останнього успішного кліку
            self.users_cache[user_id] = current_time

        return await handler(event, data)