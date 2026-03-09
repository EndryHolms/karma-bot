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
        [InlineKeyboardButton(text="✨ Карта дня (Безкоштовно)", callback_data=CB_DAILY)],
        
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
# Додай ці константи до інших зверху:
CB_CHANGE_ZODIAC = "change_zodiac"

# Словник знаків Зодіаку (щоб зручно було виводити текст)
ZODIACS = {
    "aries": "♈ Овен", "taurus": "♉ Телець", "gemini": "♊ Близнюки",
    "cancer": "♋ Рак", "leo": "♌ Лев", "virgo": "♍ Діва",
    "libra": "♎ Терези", "scorpio": "♏ Скорпіон", "sagittarius": "♐ Стрілець",
    "capricorn": "♑ Козеріг", "aquarius": "♒ Водолій", "pisces": "♓ Риби",
    "all": "🌌 Усі знаки (за замовчуванням)"
}

def broadcast_horoscope_kb() -> InlineKeyboardMarkup:
    """Кнопка, яка прикріплюється до загальної розсилки"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Надсилати тільки мій знак", callback_data=CB_CHANGE_ZODIAC)]
    ])
    return kb

def zodiac_selection_kb() -> InlineKeyboardMarkup:
    """Клавіатура вибору знаку зодіаку (з візуальним вирівнюванням)"""
    # Використано спеціальний невидимий символ '⠀' для штучного подовження слів, 
    # щоб Telegram відцентрував їх однаково.
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="♈ Овен⠀⠀⠀", callback_data="set_zodiac:aries"),
            InlineKeyboardButton(text="♉ Телець⠀", callback_data="set_zodiac:taurus"),
            InlineKeyboardButton(text="♊ Близн.⠀", callback_data="set_zodiac:gemini")
        ],
        [
            InlineKeyboardButton(text="♋ Рак⠀⠀⠀⠀", callback_data="set_zodiac:cancer"),
            InlineKeyboardButton(text="♌ Лев⠀⠀⠀⠀", callback_data="set_zodiac:leo"),
            InlineKeyboardButton(text="♍ Діва⠀⠀⠀", callback_data="set_zodiac:virgo")
        ],
        [
            InlineKeyboardButton(text="♎ Терези⠀", callback_data="set_zodiac:libra"),
            InlineKeyboardButton(text="♏ Скорп.⠀", callback_data="set_zodiac:scorpio"),
            InlineKeyboardButton(text="♐ Стріл.⠀", callback_data="set_zodiac:sagittarius")
        ],
        [
            InlineKeyboardButton(text="♑ Козеріг", callback_data="set_zodiac:capricorn"),
            InlineKeyboardButton(text="♒ Водолій", callback_data="set_zodiac:aquarius"),
            InlineKeyboardButton(text="♓ Риби⠀⠀⠀", callback_data="set_zodiac:pisces")
        ],
        [InlineKeyboardButton(text="🌌 Надсилати усі знаки", callback_data="set_zodiac:all")],
        [InlineKeyboardButton(text="🔙 Назад до профілю", callback_data="profile_balance")]
    ])
    return kb

def horoscope_share_menu_kb() -> InlineKeyboardMarkup:
    """Клавіатура для гороскопу: Поділитися + Головне меню"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        # 👇 Кнопка поділитися (відкриває список контактів у Telegram)
        [InlineKeyboardButton(
            text="🚀 Поділитися з друзями", 
            url="https://t.me/share/url?url=https://t.me/gokarma_bot&text=🔮%20Заходь%20читати%20свій%20кармічний%20гороскоп!%20Він%20сьогодні%20дуже%20життєвий%20😅"
        )],
        
        # 👇 Звичайне головне меню
        [InlineKeyboardButton(text="✨ Карта дня (Безкоштовно)", callback_data=CB_DAILY)],
        [InlineKeyboardButton(text="❤️ Любов та Стосунки (75 ⭐️)", callback_data=CB_RELATIONSHIP)],
        [InlineKeyboardButton(text="💰 Гроші та Реалізація (100 ⭐️)", callback_data=CB_CAREER)],
        [InlineKeyboardButton(text="🧘 Порада Всесвіту (25 ⭐️)", callback_data=CB_ADVICE)],
        [InlineKeyboardButton(text="👤 Моя карма (баланс)", callback_data=CB_PROFILE)],
    ])
    return kb