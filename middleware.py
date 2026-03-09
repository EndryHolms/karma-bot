import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from firebase_admin import firestore

from lexicon import get_text

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 3.0):
        # 3.0 секунди для "важких" розкладів
        self.rate_limit = rate_limit
        self.users_cache: Dict[int, float] = {}
        self.lang_cache: Dict[int, str] = {} 

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
            
            # 👇 Перевіряємо, чи це швидка кнопка навігації
            is_navigation = False
            if isinstance(event, CallbackQuery) and event.data:
                # Список префіксів для кнопок, які мають працювати швидко
                nav_prefixes = ["menu:profile", "menu:back", "change_zodiac", "set_zodiac", "set_lang"]
                is_navigation = any(event.data.startswith(prefix) for prefix in nav_prefixes)
            
            # Встановлюємо динамічний ліміт: 0.5с для меню, 3.0с для розкладів
            limit = 0.5 if is_navigation else self.rate_limit
            
            if current_time - last_time < limit:
                if isinstance(event, CallbackQuery):
                    # Показуємо попередження ТІЛЬКИ для важких розкладів
                    if not is_navigation:
                        lang = self.lang_cache.get(user_id, "uk")
                        await event.answer(get_text(lang, "magic_wait"), show_alert=True)
                    else:
                        # Для меню просто тихо ігноруємо подвійний клік (без віконця)
                        await event.answer() 
                return 
            
            self.users_cache[user_id] = current_time
            
            # Оновлюємо кеш мови
            try:
                db = data.get("db")
                if not db:
                    db = firestore.client()
                doc = db.collection("users").document(str(user_id)).get()
                if doc.exists:
                    self.lang_cache[user_id] = doc.to_dict().get("language", "uk")
            except Exception:
                pass

        return await handler(event, data)