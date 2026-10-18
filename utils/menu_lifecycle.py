from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage, SendPhoto

from utils.navigation import is_disposable_menu_text


class MainMenuLifecycleMiddleware(BaseRequestMiddleware):
    """Retire the previous main menu whenever any flow sends a new one."""

    def __init__(self, db: Any) -> None:
        self.db = db
        self._locks = [asyncio.Lock() for _ in range(64)]

    async def __call__(self, make_request, bot, method):
        if not isinstance(method, (SendMessage, SendPhoto)):
            return await make_request(bot, method)
        keyboard = getattr(method.reply_markup, "inline_keyboard", [])
        callbacks = {button.callback_data for row in keyboard for button in row}
        if not {"menu:daily", "menu:profile"}.issubset(callbacks):
            return await make_request(bot, method)

        async with self._locks[hash(str(method.chat_id)) % len(self._locks)]:
            result = await make_request(bot, method)
            reference = self.db.collection("bot_navigation").document(f"{bot.id}_{result.chat.id}")
            try:
                snapshot = await asyncio.to_thread(reference.get)
                previous = snapshot.to_dict() or {}
                disposable = is_disposable_menu_text(result.text)
                await asyncio.to_thread(reference.set, {
                    "message_id": result.message_id,
                    "disposable": disposable,
                })
            except Exception:
                logging.warning("Could not track the latest main menu", exc_info=True)
                return result

            previous_id = previous.get("message_id")
            if previous_id and previous_id != result.message_id:
                try:
                    if previous.get("disposable"):
                        await bot.delete_message(chat_id=result.chat.id, message_id=previous_id)
                    else:
                        # A welcome message or reading can also carry the main keyboard.
                        await bot.edit_message_reply_markup(
                            chat_id=result.chat.id, message_id=previous_id, reply_markup=None,
                        )
                except TelegramBadRequest:
                    # The previous screen may already have been retired on navigation.
                    pass
                except Exception:
                    logging.warning("Could not retire the previous main menu", exc_info=True)
            return result
