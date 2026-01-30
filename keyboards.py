from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# Константи для Callback Data (щоб не плутатись)
CB_DAILY = "daily_card"
CB_RELATIONSHIP = "relationship"
CB_CAREER = "career"
CB_ADVICE = "advice"
CB_PROFILE = "profile"
CB_BACK_MENU = "back_menu"

def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔮 Карта дня (Безкоштовно)", callback_data=CB_DAILY)],
        [InlineKeyboardButton(text="❤️ ❤️ Любов та Стосунки (75 ⭐)", callback_data=CB_RELATIONSHIP)],
        [InlineKeyboardButton(text="💼 Гроші та Реалізація (100 ⭐)", callback_data=CB_CAREER)],
        [InlineKeyboardButton(text="🧘 Порада Всесвіту (25 ⭐)", callback_data=CB_ADVICE)],
        # 👇 ОСЬ ТУТ ЗМІНЕНО НАЗВУ 👇
        [InlineKeyboardButton(text="👤 Моя карма (баланс)", callback_data=CB_PROFILE)],
    ])
    return kb

def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=CB_BACK_MENU)]
    ])