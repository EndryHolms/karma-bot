from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Константи для Callback Data (щоб не помилитися в буквах)
CB_DAILY = "daily_card"
CB_RELATIONSHIP = "relationship_reading"
CB_CAREER = "career_reading"
CB_ADVICE = "universe_advice"
CB_PROFILE = "profile_balance"
CB_BACK_MENU = "back_to_menu"

def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        # 👇 Змінено за вашим проханням
        [InlineKeyboardButton(text="✨ Карта дня (Free)", callback_data=CB_DAILY)],
        
        # 👇 Ваші нові назви зі скріншота
        [InlineKeyboardButton(text="❤️ Любов та Стосунки (75 ⭐️)", callback_data=CB_RELATIONSHIP)],
        [InlineKeyboardButton(text="💰 Гроші та Реалізація (100 ⭐️)", callback_data=CB_CAREER)],
        
        [InlineKeyboardButton(text="🧘 Порада Всесвіту (25 ⭐️)", callback_data=CB_ADVICE)],
        
        [InlineKeyboardButton(text="👤 Моя карма (баланс)", callback_data=CB_PROFILE)],
    ])
    return kb

def back_to_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data=CB_BACK_MENU)]
    ])
    return kb