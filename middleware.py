import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 3.0):
        # rate_limit - це затримка в секундах
        self.rate_limit = rate_limit
        # Словник, де ми пам'ятаємо, коли юзер останній раз щось натискав
        self.users_cache: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        
        user_id = None
        
        # Визначаємо ID користувача залежно від того, чи це текст, чи кнопка
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
            
        if user_id is not None:
            current_time = time.time()
            last_time = self.users_cache.get(user_id, 0.0)
            
            # Якщо пройшло менше секунд, ніж наш ліміт
            if current_time - last_time < self.rate_limit:
                # Якщо це натискання на кнопку - показуємо гарне спливаюче вікно
                if isinstance(event, CallbackQuery):
                    await event.answer("🧘 Зачекай... Магія не терпить поспіху.", show_alert=True)
                # Перериваємо обробку (охоронець не пускає далі)
                return 
            
            # Записуємо новий час
            self.users_cache[user_id] = current_time

        # Пропускаємо далі до хендлерів
        return await handler(event, data)