from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Константи
CB_DAILY = "daily_card"
CB_RELATIONSHIP = "relationship"
CB_CAREER = "career"
CB_ADVICE = "advice"
CB_PROFILE = "profile"
CB_BACK_MENU = "back_menu"

def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        # Було "Карта дня", стало "Енергія дня"
        [InlineKeyboardButton(text="✨ Карта дня (Безкоштовно)", callback_data=CB_DAILY)],
        
        # Було "Розклад на відносини", стало "Любов та Стосунки"
        [InlineKeyboardButton(text="❤️ Розклад на відносини (75 ⭐)", callback_data=CB_RELATIONSHIP)],
        
        # Було "Кар'єра та Гроші", стало "Гроші та Реалізація"
        [InlineKeyboardButton(text="💰 Кар'єра та Реалізація (100 ⭐)", callback_data=CB_CAREER)],
        
        [InlineKeyboardButton(text="🧘 Порада Всесвіту (25 ⭐)", callback_data=CB_ADVICE)],
        
        # Ваша назва
        [InlineKeyboardButton(text="👤 Моя карма (баланс)", callback_data=CB_PROFILE)],
    ])
    return kb

def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=CB_BACK_MENU)]
    ])