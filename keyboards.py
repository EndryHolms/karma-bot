from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from lexicon import get_text

CB_DAILY = "menu:daily"
CB_RELATIONSHIP = "menu:relationship"
CB_CAREER = "menu:career"
CB_ADVICE = "menu:advice"
CB_PROFILE = "menu:profile"
CB_BACK_MENU = "menu:back"
CB_CHANGE_ZODIAC = "change_zodiac"
CB_SHARE_HOROSCOPE = "horoscope:share"

_SHARE_HOROSCOPE_TEXT = {
    "uk": "📤 Поділитися з друзями",
    "en": "📤 Share with friends",
    "ru": "📤 Поделиться с друзьями",
}


def _share_text(lang: str) -> str:
    return _SHARE_HOROSCOPE_TEXT.get(lang, _SHARE_HOROSCOPE_TEXT["uk"])


def language_selection_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇦 Українська", callback_data="set_lang:uk")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang:en")],
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru")],
        ]
    )


def main_menu_kb(lang: str = "uk") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, "menu_daily"), callback_data=CB_DAILY)],
            [InlineKeyboardButton(text=get_text(lang, "menu_love"), callback_data=CB_RELATIONSHIP)],
            [InlineKeyboardButton(text=get_text(lang, "menu_career"), callback_data=CB_CAREER)],
            [InlineKeyboardButton(text=get_text(lang, "menu_advice"), callback_data=CB_ADVICE)],
            [InlineKeyboardButton(text=get_text(lang, "menu_profile"), callback_data=CB_PROFILE)],
        ]
    )


def back_to_menu_kb(lang: str = "uk") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data=CB_BACK_MENU)]
        ]
    )


def horoscope_share_menu_kb(lang: str = "uk") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_share_text(lang), callback_data=CB_SHARE_HOROSCOPE)],
            [InlineKeyboardButton(text=get_text(lang, "menu_daily"), callback_data=CB_DAILY)],
            [InlineKeyboardButton(text=get_text(lang, "menu_love"), callback_data=CB_RELATIONSHIP)],
            [InlineKeyboardButton(text=get_text(lang, "menu_career"), callback_data=CB_CAREER)],
            [InlineKeyboardButton(text=get_text(lang, "menu_advice"), callback_data=CB_ADVICE)],
            [InlineKeyboardButton(text=get_text(lang, "menu_profile"), callback_data=CB_PROFILE)],
        ]
    )


def zodiac_selection_kb(lang: str = "uk") -> InlineKeyboardMarkup:
    z = get_text(lang, "zodiacs")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=z["aries"], callback_data="set_zodiac:aries"),
                InlineKeyboardButton(text=z["taurus"], callback_data="set_zodiac:taurus"),
                InlineKeyboardButton(text=z["gemini"], callback_data="set_zodiac:gemini"),
            ],
            [
                InlineKeyboardButton(text=z["cancer"], callback_data="set_zodiac:cancer"),
                InlineKeyboardButton(text=z["leo"], callback_data="set_zodiac:leo"),
                InlineKeyboardButton(text=z["virgo"], callback_data="set_zodiac:virgo"),
            ],
            [
                InlineKeyboardButton(text=z["libra"], callback_data="set_zodiac:libra"),
                InlineKeyboardButton(text=z["scorpio"], callback_data="set_zodiac:scorpio"),
                InlineKeyboardButton(text=z["sagittarius"], callback_data="set_zodiac:sagittarius"),
            ],
            [
                InlineKeyboardButton(text=z["capricorn"], callback_data="set_zodiac:capricorn"),
                InlineKeyboardButton(text=z["aquarius"], callback_data="set_zodiac:aquarius"),
                InlineKeyboardButton(text=z["pisces"], callback_data="set_zodiac:pisces"),
            ],
            [InlineKeyboardButton(text=get_text(lang, "btn_all_signs"), callback_data="set_zodiac:all")],
            [InlineKeyboardButton(text=get_text(lang, "btn_back_profile"), callback_data=CB_PROFILE)],
        ]
    )