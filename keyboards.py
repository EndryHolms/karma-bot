from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


CB_DAILY = "daily_card"
CB_RELATIONSHIP = "relationship_reading"
CB_CAREER = "career_reading"
CB_ADVICE = "universe_advice"
CB_PROFILE = "profile"
CB_BACK_MENU = "back_menu"


def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔮 Карта дня (Безкоштовно)", callback_data=CB_DAILY)
    kb.button(text="❤️ Розклад на відносини (75 ⭐️)", callback_data=CB_RELATIONSHIP)
    kb.button(text="💼 Кар'єра та Гроші (100 ⭐️)", callback_data=CB_CAREER)
    kb.button(text="🧘 Порада Всесвіту (25 ⭐️)", callback_data=CB_ADVICE)
    kb.button(text="👤 Мій профіль", callback_data=CB_PROFILE)
    kb.adjust(1)
    return kb.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад в меню", callback_data=CB_BACK_MENU)
    return kb.as_markup()
