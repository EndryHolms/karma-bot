import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from firebase_admin import firestore

from lexicon import get_text

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 3.0):
        self.rate_limit = rate_limit
        self.users_cache: Dict[int, float] = {}
        # 👇 Кеш мов для миттєвого доступу без бази даних
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
            
            if current_time - last_time < self.rate_limit:
                if isinstance(event, CallbackQuery):
                    # 👇 Беремо мову з кешу, або українську за замовчуванням
                    lang = self.lang_cache.get(user_id, "uk")
                    await event.answer(get_text(lang, "magic_wait"), show_alert=True)
                return 
            
            self.users_cache[user_id] = current_time
            
            # 👇 Оновлюємо кеш мови для користувача на майбутнє (безпечно)
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