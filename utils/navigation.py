import logging

from aiogram.types import InlineKeyboardMarkup, Message


async def send_next_screen(message: Message, text: str, keyboard: InlineKeyboardMarkup) -> Message:
    """Continue navigation at the bottom of the chat and retire the old buttons."""
    next_message = await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    try:
        await message.edit_reply_markup(reply_markup=None)
    except Exception:
        logging.warning("Could not remove previous navigation keyboard", exc_info=True)
    return next_message
