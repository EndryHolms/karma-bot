import logging

from aiogram.types import InlineKeyboardMarkup, Message

from lexicon import get_text


def is_disposable_menu_text(text: str | None) -> bool:
    return bool(text and text.strip() in {
        get_text(lang, key)
        for lang in ("uk", "en", "ru")
        for key in ("main_menu_title", "more_action_btn")
    })


async def send_next_screen(message: Message, text: str, keyboard: InlineKeyboardMarkup, *, delete_previous: bool = False) -> Message:
    """Continue navigation at the bottom of the chat and retire the old buttons."""
    next_message = await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    if delete_previous or is_disposable_menu_text(message.text):
        try:
            await message.delete()
            return next_message
        except Exception:
            logging.warning("Could not delete previous navigation screen", exc_info=True)
    try:
        await message.edit_reply_markup(reply_markup=None)
    except Exception:
        logging.warning("Could not remove previous navigation keyboard", exc_info=True)
    return next_message
