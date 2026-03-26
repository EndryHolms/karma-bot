import asyncio
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from firebase_db import get_user_language, log_chat_message
from lexicon import get_text


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 3.0):
        self.rate_limit = rate_limit
        self.ai_cache: Dict[int, float] = {}
        self.ai_inflight: set[int] = set()
        self.ai_prefixes = (
            "menu:daily",
            "menu:relationship",
            "menu:career",
            "menu:advice",
        )

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        is_ai_request = (
            isinstance(event, CallbackQuery)
            and bool(event.data)
            and any(event.data.startswith(prefix) for prefix in self.ai_prefixes)
        )

        if not is_ai_request:
            return await handler(event, data)

        current_time = time.monotonic()
        last_time = self.ai_cache.get(user_id, 0.0)

        if user_id in self.ai_inflight or current_time - last_time < self.rate_limit:
            db = data.get("db")
            lang = await get_user_language(db, user_id) if db else "uk"
            await event.answer(get_text(lang, "magic_wait"), show_alert=True)
            return None

        self.ai_cache[user_id] = current_time
        self.ai_inflight.add(user_id)
        try:
            return await handler(event, data)
        finally:
            self.ai_inflight.discard(user_id)


class ChatLoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text:
            db = data.get("db")
            if db and event.from_user:
                asyncio.create_task(
                    log_chat_message(
                        db=db,
                        user_id=event.from_user.id,
                        role="user",
                        text=event.text,
                    )
                )

        return await handler(event, data)
