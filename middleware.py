import time
from typing import Any, Awaitable, Callable, Dict
from firebase_db import get_user_language
from lexicon import get_text
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 3.0):
        self.rate_limit = rate_limit
        # Тепер ми зберігаємо час для КОЖНОЇ КОНКРЕТНОЇ ДІЇ (наприклад, "id_користувача:назва_кнопки")
        self.users_cache: Dict[str, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        
        user_id = None
        action_id = "default"
        
        # Визначаємо ID користувача та яку саме дію він робить
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            action_id = "text_message" # Для текстових повідомлень окремий ліміт
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
            action_id = event.data or "callback" # Беремо callback_data (назву кнопки)
            
        if user_id is not None:
            # Створюємо унікальний ключ для перевірки (наприклад: "123456789:daily_card")
            cache_key = f"{user_id}:{action_id}"
            current_time = time.time()
            last_time = self.users_cache.get(cache_key, 0.0)
            
            # Якщо пройшло менше секунд, ніж наш ліміт ДЛЯ ЦІЄЇ КОНКРЕТНОЇ ДІЇ
            if current_time - last_time < self.rate_limit:
                if isinstance(event, CallbackQuery):
                    await event.answer("🧘 Зачекай... Магія не терпить поспіху.", show_alert=True)
                return 
            
            # Записуємо новий час для цієї конкретної дії
            self.users_cache[cache_key] = current_time

        # Пропускаємо далі
        return await handler(event, data)