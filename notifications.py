import asyncio
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any

import pytz
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from firebase_admin import firestore

from firebase_db import log_chat_message
from gemini_runtime import generate_content
from keyboards import main_menu_kb

_MONTHLY_REMINDER_TEXT = {
    "uk": "✨ <i>Всесвіт давно не чув твого запиту...</i>\n\nТи вже колись відкривав свою Карту Дня, але давно не повертався. Можливо, зараз саме час знову подивитися, які енергії тебе супроводжують 👇",
    "en": "✨ <i>The Universe has not heard from you in a while...</i>\n\nYou have opened your Card of the Day before, but it has been a while since your last visit. Maybe now is the right time to check what energies are around you 👇",
    "ru": "✨ <i>Вселенная давно не слышала твоего запроса...</i>\n\nТы уже открывал свою Карту Дня раньше, но давно не возвращался. Возможно, сейчас самое время снова посмотреть, какие энергии тебя сопровождают 👇",
}

_HOROSCOPE_TITLE = {
    "uk": "🔮 <b>Кармічний гороскоп на {date}:</b>",
    "en": "🔮 <b>Karmic horoscope for {date}:</b>",
    "ru": "🔮 <b>Кармический гороскоп на {date}:</b>",
}

_HOROSCOPE_FOLLOWUP = {
    "uk": "💫 <i>Що підказує твоя інтуїція далі?</i> 👇",
    "en": "💫 <i>What is your intuition telling you to do next?</i> 👇",
    "ru": "💫 <i>Что подсказывает твоя интуиция дальше?</i> 👇",
}

_HOROSCOPE_SOURCE = {
    "uk": "🔮 Це лише загальний знак. Персональна відповідь — у <a href=\"{link}\">Karma</a>",
    "en": "🔮 This is only a general sign. Your personal answer is in <a href=\"{link}\">Karma</a>",
    "ru": "🔮 Это лишь общий знак. Персональный ответ — в <a href=\"{link}\">Karma</a>",
}

_HOROSCOPE_SIGNS = {
    "uk": {
        "aries": "Овен",
        "taurus": "Телець",
        "gemini": "Близнюки",
        "cancer": "Рак",
        "leo": "Лев",
        "virgo": "Діва",
        "libra": "Терези",
        "scorpio": "Скорпіон",
        "sagittarius": "Стрілець",
        "capricorn": "Козеріг",
        "aquarius": "Водолій",
        "pisces": "Риби",
    },
    "en": {
        "aries": "Aries",
        "taurus": "Taurus",
        "gemini": "Gemini",
        "cancer": "Cancer",
        "leo": "Leo",
        "virgo": "Virgo",
        "libra": "Libra",
        "scorpio": "Scorpio",
        "sagittarius": "Sagittarius",
        "capricorn": "Capricorn",
        "aquarius": "Aquarius",
        "pisces": "Pisces",
    },
    "ru": {
        "aries": "Овен",
        "taurus": "Телец",
        "gemini": "Близнецы",
        "cancer": "Рак",
        "leo": "Лев",
        "virgo": "Дева",
        "libra": "Весы",
        "scorpio": "Скорпион",
        "sagittarius": "Стрелец",
        "capricorn": "Козерог",
        "aquarius": "Водолей",
        "pisces": "Рыбы",
    },
}

_HOROSCOPE_LANGS = ("uk", "en", "ru")
_ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "469764985").split(",")
    if value.strip().isdigit()
}
_ZODIAC_EMOJIS = {
    "aries": "\u2648",
    "taurus": "\u2649",
    "gemini": "\u264a",
    "cancer": "\u264b",
    "leo": "\u264c",
    "virgo": "\u264d",
    "libra": "\u264e",
    "scorpio": "\u264f",
    "sagittarius": "\u2650",
    "capricorn": "\u2651",
    "aquarius": "\u2652",
    "pisces": "\u2653",
}
_EMERGENCY_HOROSCOPE_TEMPLATES = {
    "uk": (
        "\u041e\u0431\u0435\u0440\u0456\u0442\u044c \u043e\u0434\u0438\u043d \u043a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u0438\u0439 \u043a\u0440\u043e\u043a \u0456 \u0437\u0440\u043e\u0431\u0456\u0442\u044c \u0439\u043e\u0433\u043e \u0434\u043e \u0442\u043e\u0433\u043e, \u044f\u043a \u0441\u0443\u043c\u043d\u0456\u0432\u0438 \u0441\u043a\u043b\u0438\u0447\u0443\u0442\u044c \u043d\u0430\u0440\u0430\u0434\u0443.",
        "\u041d\u0435 \u043f\u043e\u0441\u043f\u0456\u0448\u0430\u0439\u0442\u0435 \u0432\u0456\u0434\u043f\u043e\u0432\u0456\u0434\u0430\u0442\u0438: \u0441\u044c\u043e\u0433\u043e\u0434\u043d\u0456 \u043f\u0430\u0443\u0437\u0430 \u0441\u043a\u0430\u0436\u0435 \u0431\u0456\u043b\u044c\u0448\u0435, \u043d\u0456\u0436 \u0437\u0430\u0439\u0432\u0435 \u043f\u043e\u044f\u0441\u043d\u0435\u043d\u043d\u044f.",
        "\u041c\u0430\u043b\u0435\u043d\u044c\u043a\u0430 \u0437\u043c\u0456\u043d\u0430 \u0443 \u0437\u0432\u0438\u0447\u043d\u043e\u043c\u0443 \u043c\u0430\u0440\u0448\u0440\u0443\u0442\u0456 \u043c\u043e\u0436\u0435 \u043f\u0440\u0438\u0432\u0435\u0441\u0442\u0438 \u0434\u043e \u043f\u043e\u0442\u0440\u0456\u0431\u043d\u043e\u0457 \u0440\u043e\u0437\u043c\u043e\u0432\u0438.",
        "\u0411\u0435\u0440\u0435\u0436\u0456\u0442\u044c \u0435\u043d\u0435\u0440\u0433\u0456\u044e \u0434\u043b\u044f \u0442\u043e\u0433\u043e, \u0449\u043e \u0441\u043f\u0440\u0430\u0432\u0434\u0456 \u0437\u0430\u043b\u0435\u0436\u0438\u0442\u044c \u0432\u0456\u0434 \u0432\u0430\u0441.",
        "\u0414\u043e\u0432\u0456\u0440\u0442\u0435\u0441\u044f \u0444\u0430\u043a\u0442\u0430\u043c, \u0430\u043b\u0435 \u0437\u0430\u043b\u0438\u0448\u0442\u0435 \u0442\u0440\u043e\u0445\u0438 \u043c\u0456\u0441\u0446\u044f \u0434\u043b\u044f \u043f\u0440\u0438\u0454\u043c\u043d\u043e\u0433\u043e \u0441\u044e\u0440\u043f\u0440\u0438\u0437\u0443.",
        "\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430 \u0434\u0440\u0456\u0431\u043d\u0430 \u0441\u043f\u0440\u0430\u0432\u0430 \u043f\u043e\u0432\u0435\u0440\u043d\u0435 \u0432\u0456\u0434\u0447\u0443\u0442\u0442\u044f \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044e \u043d\u0430\u0434 \u0432\u0435\u043b\u0438\u043a\u0438\u043c\u0438 \u043f\u043b\u0430\u043d\u0430\u043c\u0438.",
        "\u0427\u0456\u0442\u043a\u0430 \u043c\u0435\u0436\u0430 \u0441\u044c\u043e\u0433\u043e\u0434\u043d\u0456 \u043a\u043e\u0440\u0438\u0441\u043d\u0456\u0448\u0430 \u0437\u0430 \u043c\u043e\u0432\u0447\u0430\u0437\u043d\u0443 \u043e\u0431\u0440\u0430\u0437\u0443.",
        "\u041d\u0435 \u0432\u0438\u043c\u0430\u0433\u0430\u0439\u0442\u0435 \u0432\u0456\u0434 \u0441\u0435\u0431\u0435 \u0456\u0434\u0435\u0430\u043b\u044c\u043d\u043e\u0433\u043e \u0442\u0435\u043c\u043f\u0443 \u2014 \u0441\u0442\u0430\u0431\u0456\u043b\u044c\u043d\u0456\u0441\u0442\u044c \u0443\u0436\u0435 \u0454 \u043f\u0435\u0440\u0435\u043c\u043e\u0433\u043e\u044e.",
        "\u0412\u0438\u043f\u0430\u0434\u043a\u043e\u0432\u0430 \u0456\u0434\u0435\u044f \u0432\u0430\u0440\u0442\u0430 \u043d\u043e\u0442\u0430\u0442\u043a\u0438: \u0457\u0457 \u0441\u0435\u043d\u0441 \u0432\u0456\u0434\u043a\u0440\u0438\u0454\u0442\u044c\u0441\u044f \u0442\u0440\u043e\u0445\u0438 \u043f\u0456\u0437\u043d\u0456\u0448\u0435.",
        "\u0424\u0456\u043d\u0430\u043d\u0441\u043e\u0432\u0456 \u0440\u0456\u0448\u0435\u043d\u043d\u044f \u043a\u0440\u0430\u0449\u0435 \u043f\u0435\u0440\u0435\u0432\u0456\u0440\u0438\u0442\u0438 \u0434\u0432\u0456\u0447\u0456, \u0430 \u0434\u043e\u0431\u0440\u0456 \u0441\u043b\u043e\u0432\u0430 \u0441\u043a\u0430\u0437\u0430\u0442\u0438 \u043e\u0434\u0440\u0430\u0437\u0443.",
        "\u0417\u043d\u0430\u0439\u0434\u0456\u0442\u044c \u0447\u0430\u0441 \u0434\u043b\u044f \u0442\u0438\u0448\u0456: \u0432\u0456\u0434\u043f\u043e\u0432\u0456\u0434\u044c \u0443\u0436\u0435 \u0431\u043b\u0438\u0436\u0447\u0435, \u043d\u0456\u0436 \u0437\u0434\u0430\u0454\u0442\u044c\u0441\u044f.",
        "\u0421\u044c\u043e\u0433\u043e\u0434\u043d\u0456 \u0433\u0443\u043c\u043e\u0440 \u0434\u043e\u043f\u043e\u043c\u043e\u0436\u0435 \u043f\u0440\u043e\u0439\u0442\u0438 \u0442\u0430\u043c, \u0434\u0435 \u0441\u0435\u0440\u0439\u043e\u0437\u043d\u0456\u0441\u0442\u044c \u0441\u0442\u0432\u043e\u0440\u044e\u0454 \u0437\u0430\u0439\u0432\u0456 \u043f\u0435\u0440\u0435\u0448\u043a\u043e\u0434\u0438.",
    ),
    "en": (
        "Choose one concrete step and take it before doubt calls a meeting.",
        "Do not rush your answer; today a pause can say more than another explanation.",
        "A small change in your usual route may lead to the conversation you need.",
        "Save your energy for what is genuinely within your control.",
        "Trust the facts, but leave a little room for a pleasant surprise.",
        "Finishing one small task will restore confidence in your bigger plans.",
        "A clear boundary will serve you better today than silent resentment.",
        "Do not demand a perfect pace from yourself; consistency is already a win.",
        "A passing idea deserves a note; its meaning will become clear later.",
        "Double-check money decisions, but say kind words without delay.",
        "Make room for silence; the answer is closer than it seems.",
        "Humor will get you through places where seriousness creates extra obstacles.",
    ),
    "ru": (
        "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043e\u0434\u0438\u043d \u043a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u044b\u0439 \u0448\u0430\u0433 \u0438 \u0441\u0434\u0435\u043b\u0430\u0439\u0442\u0435 \u0435\u0433\u043e \u0434\u043e \u0442\u043e\u0433\u043e, \u043a\u0430\u043a \u0441\u043e\u043c\u043d\u0435\u043d\u0438\u044f \u0441\u043e\u0437\u043e\u0432\u0443\u0442 \u0441\u043e\u0432\u0435\u0449\u0430\u043d\u0438\u0435.",
        "\u041d\u0435 \u0441\u043f\u0435\u0448\u0438\u0442\u0435 \u043e\u0442\u0432\u0435\u0447\u0430\u0442\u044c: \u0441\u0435\u0433\u043e\u0434\u043d\u044f \u043f\u0430\u0443\u0437\u0430 \u0441\u043a\u0430\u0436\u0435\u0442 \u0431\u043e\u043b\u044c\u0448\u0435, \u0447\u0435\u043c \u043b\u0438\u0448\u043d\u0435\u0435 \u043e\u0431\u044a\u044f\u0441\u043d\u0435\u043d\u0438\u0435.",
        "\u041d\u0435\u0431\u043e\u043b\u044c\u0448\u0430\u044f \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u0430 \u0432 \u043f\u0440\u0438\u0432\u044b\u0447\u043d\u043e\u043c \u043c\u0430\u0440\u0448\u0440\u0443\u0442\u0435 \u043c\u043e\u0436\u0435\u0442 \u043f\u0440\u0438\u0432\u0435\u0441\u0442\u0438 \u043a \u043d\u0443\u0436\u043d\u043e\u043c\u0443 \u0440\u0430\u0437\u0433\u043e\u0432\u043e\u0440\u0443.",
        "\u0411\u0435\u0440\u0435\u0433\u0438\u0442\u0435 \u044d\u043d\u0435\u0440\u0433\u0438\u044e \u0434\u043b\u044f \u0442\u043e\u0433\u043e, \u0447\u0442\u043e \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0442\u0435\u043b\u044c\u043d\u043e \u0437\u0430\u0432\u0438\u0441\u0438\u0442 \u043e\u0442 \u0432\u0430\u0441.",
        "\u0414\u043e\u0432\u0435\u0440\u044c\u0442\u0435\u0441\u044c \u0444\u0430\u043a\u0442\u0430\u043c, \u043d\u043e \u043e\u0441\u0442\u0430\u0432\u044c\u0442\u0435 \u043d\u0435\u043c\u043d\u043e\u0433\u043e \u043c\u0435\u0441\u0442\u0430 \u0434\u043b\u044f \u043f\u0440\u0438\u044f\u0442\u043d\u043e\u0433\u043e \u0441\u044e\u0440\u043f\u0440\u0438\u0437\u0430.",
        "\u0417\u0430\u0432\u0435\u0440\u0448\u0451\u043d\u043d\u043e\u0435 \u043d\u0435\u0431\u043e\u043b\u044c\u0448\u043e\u0435 \u0434\u0435\u043b\u043e \u0432\u0435\u0440\u043d\u0451\u0442 \u0443\u0432\u0435\u0440\u0435\u043d\u043d\u043e\u0441\u0442\u044c \u0432 \u0431\u043e\u043b\u044c\u0448\u0438\u0445 \u043f\u043b\u0430\u043d\u0430\u0445.",
        "\u0427\u0451\u0442\u043a\u0430\u044f \u0433\u0440\u0430\u043d\u0438\u0446\u0430 \u0441\u0435\u0433\u043e\u0434\u043d\u044f \u043f\u043e\u043b\u0435\u0437\u043d\u0435\u0435 \u043c\u043e\u043b\u0447\u0430\u043b\u0438\u0432\u043e\u0439 \u043e\u0431\u0438\u0434\u044b.",
        "\u041d\u0435 \u0442\u0440\u0435\u0431\u0443\u0439\u0442\u0435 \u043e\u0442 \u0441\u0435\u0431\u044f \u0438\u0434\u0435\u0430\u043b\u044c\u043d\u043e\u0433\u043e \u0442\u0435\u043c\u043f\u0430 \u2014 \u0441\u0442\u0430\u0431\u0438\u043b\u044c\u043d\u043e\u0441\u0442\u044c \u0443\u0436\u0435 \u044f\u0432\u043b\u044f\u0435\u0442\u0441\u044f \u043f\u043e\u0431\u0435\u0434\u043e\u0439.",
        "\u0421\u043b\u0443\u0447\u0430\u0439\u043d\u0430\u044f \u0438\u0434\u0435\u044f \u0434\u043e\u0441\u0442\u043e\u0439\u043d\u0430 \u0437\u0430\u043c\u0435\u0442\u043a\u0438: \u0435\u0451 \u0441\u043c\u044b\u0441\u043b \u0440\u0430\u0441\u043a\u0440\u043e\u0435\u0442\u0441\u044f \u043d\u0435\u043c\u043d\u043e\u0433\u043e \u043f\u043e\u0437\u0436\u0435.",
        "\u0424\u0438\u043d\u0430\u043d\u0441\u043e\u0432\u044b\u0435 \u0440\u0435\u0448\u0435\u043d\u0438\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0434\u0432\u0430\u0436\u0434\u044b, \u0430 \u0434\u043e\u0431\u0440\u044b\u0435 \u0441\u043b\u043e\u0432\u0430 \u0441\u043a\u0430\u0436\u0438\u0442\u0435 \u0441\u0440\u0430\u0437\u0443.",
        "\u041d\u0430\u0439\u0434\u0438\u0442\u0435 \u0432\u0440\u0435\u043c\u044f \u0434\u043b\u044f \u0442\u0438\u0448\u0438\u043d\u044b: \u043e\u0442\u0432\u0435\u0442 \u0443\u0436\u0435 \u0431\u043b\u0438\u0436\u0435, \u0447\u0435\u043c \u043a\u0430\u0436\u0435\u0442\u0441\u044f.",
        "\u0421\u0435\u0433\u043e\u0434\u043d\u044f \u044e\u043c\u043e\u0440 \u043f\u043e\u043c\u043e\u0436\u0435\u0442 \u043f\u0440\u043e\u0439\u0442\u0438 \u0442\u0430\u043c, \u0433\u0434\u0435 \u0441\u0435\u0440\u044c\u0451\u0437\u043d\u043e\u0441\u0442\u044c \u0441\u043e\u0437\u0434\u0430\u0451\u0442 \u043b\u0438\u0448\u043d\u0438\u0435 \u043f\u0440\u0435\u043f\u044f\u0442\u0441\u0442\u0432\u0438\u044f.",
    ),
}
_GENERATION_RETRY_DELAYS = (0, 30, 90)
_HOROSCOPE_BATCH_DAYS = 1
_DELIVERY_LOCK_STALE_MINUTES = 15
_FIRESTORE_TIMEOUT_SECONDS = 30
_DAILY_JOB_TIMEOUT_SECONDS = 10 * 60

# Список тем для урізноманітнення гороскопів
_DAILY_THEMES = [
    "день космічної іронії та побутового абсурду",
    "день агресивної мотивації від Всесвіту",
    "день екзистенційної кризи та холодного чаю",
    "день несподіваних фінансових пророцтв",
    "день, коли інтуїція працює через раз",
    "день розбитих ілюзій та нових надій",
    "день, коли доля грає з вами в гру 'ану вгадай'",
    "день офісного дзену та паперового хаосу",
    "день, коли Всесвіт поводиться як токсичний колишній",
    "день тотального ретрограду всього на світі",
    "день, коли ваш внутрішній критик пішов у відпустку",
    "день кармічних боргів та дрібної решти",
    "день, коли навіть кавомашина натякає на зміни",
    "день великих планів і дуже маленьких кроків",
    "день космічного сарказму щодо ваших дедлайнів",
    "день, коли треба просто плисти за течією, навіть якщо це течія борщу",
    "день вибору між 'треба' та 'не хочу'",
    "день, коли зорі шепочуть дурниці",
    "день зустрічі з власною лінню віч-на-віч",
    "день, коли кожна дрібниця має прихований зміст (або ні)",
    "день, коли 'пізніше' настало вже зараз",
]


def _get_daily_theme(date_key: str) -> str:
    # Вибираємо тему на основі дати (стабільно для одного дня)
    try:
        day_val = int(date_key.split("-")[-1])
        return _DAILY_THEMES[day_val % len(_DAILY_THEMES)]
    except (IndexError, ValueError):
        return _DAILY_THEMES[0]


def _localized(mapping: dict[str, str], lang: str) -> str:
    return mapping.get(lang, mapping["uk"])


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def _daily_horoscope_doc(db: firestore.Client, date_key: str):
    return db.collection("daily_horoscopes").document(date_key)


async def _load_users(db: firestore.Client) -> list[Any]:
    def _read_sync() -> list[Any]:
        return list(
            db.collection("users").stream(timeout=_FIRESTORE_TIMEOUT_SECONDS)
        )

    return await asyncio.wait_for(
        asyncio.to_thread(_read_sync),
        timeout=_FIRESTORE_TIMEOUT_SECONDS + 5,
    )


async def _store_share_text(db: firestore.Client, user_id: str, text: str, date_key: str) -> None:
    def _write_sync() -> None:
        db.collection("users").document(user_id).set(
            {
                "last_horoscope_share_text": text,
                "last_horoscope_share_date": date_key,
            },
            merge=True,
        )

    await asyncio.to_thread(_write_sync)


async def _mark_monthly_reminder_sent(db: firestore.Client, user_id: str, month_key: str) -> None:
    def _write_sync() -> None:
        db.collection("users").document(user_id).set(
            {"last_monthly_card_reminder_month": month_key},
            merge=True,
        )

    await asyncio.to_thread(_write_sync)


async def _get_cached_horoscope_payload(db: firestore.Client, date_key: str) -> dict[str, dict[str, str]] | None:
    def _read_sync() -> dict[str, dict[str, str]] | None:
        snap = _daily_horoscope_doc(db, date_key).get(
            timeout=_FIRESTORE_TIMEOUT_SECONDS
        )
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        payload = data.get("payload")
        return payload if isinstance(payload, dict) else None

    return await asyncio.to_thread(_read_sync)


async def _store_cached_horoscope_payload(
    db: firestore.Client,
    date_key: str,
    payload: dict[str, dict[str, str]],
    source: str = "gemini",
) -> None:
    def _write_sync() -> None:
        _daily_horoscope_doc(db, date_key).set(
            {
                "source": source,
                "payload": payload,
                "created_at": firestore.SERVER_TIMESTAMP,
                "generation_error": firestore.DELETE_FIELD,
            },
            merge=True,
        )

    await asyncio.to_thread(_write_sync)

async def _notify_admins_local_horoscope(bot: Bot, date_key: str, reason: str) -> None:
    message = (
        "\u26a0\ufe0f \u0412\u0438\u043a\u043e\u0440\u0438\u0441\u0442\u0430\u043d\u043e \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u0438\u0439 \u0433\u043e\u0440\u043e\u0441\u043a\u043e\u043f\n\n"
        f"\u0414\u0430\u0442\u0430: {date_key}\n"
        "Gemini \u043d\u0435 \u0437\u043c\u0456\u0433 \u0437\u0433\u0435\u043d\u0435\u0440\u0443\u0432\u0430\u0442\u0438 \u043d\u043e\u0432\u0438\u0439 \u0433\u043e\u0440\u043e\u0441\u043a\u043e\u043f, \u0442\u043e\u043c\u0443 \u0431\u043e\u0442 "
        "\u043f\u0435\u0440\u0435\u0439\u0448\u043e\u0432 \u043d\u0430 \u0430\u0432\u0430\u0440\u0456\u0439\u043d\u0438\u0439 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u0438\u0439 \u0442\u0435\u043a\u0441\u0442.\n\n"
        f"\u041f\u0440\u0438\u0447\u0438\u043d\u0430: {reason}"
    )
    for admin_id in _ADMIN_IDS:
        try:
            await bot.send_message(admin_id, message)
        except Exception as exc:
            logging.warning(
                "HOROSCOPE_ADMIN_ALERT_FAILED admin_id=%s error_type=%s error=%s",
                admin_id,
                type(exc).__name__,
                exc,
            )




async def _set_generation_error(db: firestore.Client, date_key: str, message: str, attempt: int) -> None:
    def _write_sync() -> None:
        _daily_horoscope_doc(db, date_key).set(
            {
                "generation_error": message,
                "generation_attempt": attempt,
                "generation_failed_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )

    try:
        await asyncio.to_thread(_write_sync)
    except Exception as exc:
        logging.warning(
            "HOROSCOPE_GENERATION_ERROR_WRITE_FAILED date_key=%s error_type=%s error=%s",
            date_key,
            type(exc).__name__,
            exc,
        )


async def _claim_delivery(db: firestore.Client, date_key: str, now: datetime) -> bool:
    def _tx_sync() -> bool:
        ref = _daily_horoscope_doc(db, date_key)
        now_iso = now.isoformat()
        stale_before_iso = (now - timedelta(minutes=_DELIVERY_LOCK_STALE_MINUTES)).isoformat()

        @firestore.transactional
        def _run(transaction: firestore.Transaction) -> bool:
            snap = ref.get(
                transaction=transaction,
                timeout=_FIRESTORE_TIMEOUT_SECONDS,
            )
            data = snap.to_dict() or {}

            if data.get("delivery_completed_at"):
                return False

            started_at = data.get("delivery_started_at")
            if started_at and isinstance(started_at, str) and started_at > stale_before_iso:
                return False

            transaction.set(
                ref,
                {
                    "delivery_started_at": now_iso,
                    "delivery_error": firestore.DELETE_FIELD,
                },
                merge=True,
            )
            return True

        transaction = db.transaction()
        return _run(transaction)

    return await asyncio.to_thread(_tx_sync)


async def _mark_delivery_completed(db: firestore.Client, date_key: str, sent_count: int) -> None:
    def _write_sync() -> None:
        _daily_horoscope_doc(db, date_key).set(
            {
                "delivery_completed_at": datetime.utcnow().isoformat(),
                "delivery_sent_count": sent_count,
                "delivery_error": firestore.DELETE_FIELD,
                "delivery_started_at": firestore.DELETE_FIELD,
            },
            merge=True,
            timeout=_FIRESTORE_TIMEOUT_SECONDS,
        )

    await asyncio.to_thread(_write_sync)


async def _mark_delivery_error(db: firestore.Client, date_key: str, message: str) -> None:
    def _write_sync() -> None:
        _daily_horoscope_doc(db, date_key).set(
            {
                "delivery_error": message,
                "delivery_failed_at": datetime.utcnow().isoformat(),
                "delivery_started_at": firestore.DELETE_FIELD,
            },
            merge=True,
            timeout=_FIRESTORE_TIMEOUT_SECONDS,
        )

    await asyncio.to_thread(_write_sync)


def _build_horoscope_prompt(day_configs: list[dict[str, str]]) -> str:
    # day_configs contains list of {"date": "YYYY-MM-DD", "theme": "...", "label": "DD.MM"}
    requests_str = "\n".join([f"DATE:{c['date']} | THEME: {c['theme']}" for c in day_configs])
    
    return (
        f"Generate daily horoscopes for the following dates and themes:\n{requests_str}\n\n"
        f"For EACH date, provide 3 sections: LANG:uk, LANG:en, LANG:ru. "
        f"Tone: witty, ironic, life-like, with sharp sarcasm. Use unexpected metaphors. "
        f"STRICT RULE: You are FORBIDDEN from using standard zodiac clichés. "
        f"BANNED themes for Leo: kings, thrones, royalty, greatness, crowns, majesty. "
        f"BANNED themes for Taurus: food, eating, stubbornness. "
        f"BANNED themes for Pisces: crying, tears, dreams, magic. "
        f"BANNED themes for Scorpio: revenge, poison, darkness. "
        f"Instead of astrology tropes, describe their day using purely mundane, random objects (cold coffee, Wi-Fi signals, broken zippers, tangled headphones, tax reports, missed alarms). "
        f"CRITICAL: Do NOT repeat metaphors, themes, or sentence structures! Every single prediction across all dates and signs MUST be highly distinct and unique. "
        f"The text for each sign must be exactly ONE medium-length sentence, punchy and unique. "
        f"Each language section must contain exactly 12 horoscope lines and no extra introduction or conclusion. "
        f"Use exactly this format inside each language section: zodiac emoji, localized sign name, space, hyphen, space, the sentence. "
        f"Put one empty line between lines. "
        f"Use these exact sign names for each language. "
        f"For LANG:uk use: Овен, Телець, Близнюки, Рак, Лев, Діва, Терези, Скорпіон, Стрілець, Козеріг, Водолій, Риби. "
        f"For LANG:en use: Aries, Taurus, Gemini, Cancer, Leo, Virgo, Libra, Scorpio, Sagittarius, Capricorn, Aquarius, Pisces. "
        f"For LANG:ru use: Овен, Телец, Близнецы, Рак, Лев, Дева, Весы, Скорпион, Стрелец, Козерог, Водолей, Рыбы. "
        f"Structure your entire response as a sequence of date blocks:\n\n"
        f"DATE:YYYY-MM-DD\n"
        f"LANG:uk\n"
        f"♈ Овен - ...\n\n"
        f"LANG:en\n"
        f"♈ Aries - ...\n\n"
        f"LANG:ru\n"
        f"♈ Овен - ...\n\n"
        f"(repeat for other dates)"
    )


def _extract_language_block(raw_text: str, lang: str) -> str:
    marker = f"LANG:{lang}"
    start = raw_text.find(marker)
    if start == -1:
        return ""
    start_pos: int = start + len(marker)
    remainder: str = raw_text[start_pos:].lstrip()
    next_positions: list[int] = []
    for other in _HOROSCOPE_LANGS:
        if other == lang:
            continue
        pos = remainder.find(f"LANG:{other}")
        if pos != -1:
            next_positions.append(pos)
    end = min(next_positions) if next_positions else len(remainder)
    return remainder[:end].strip()


def _build_language_payload(block: str, lang: str) -> dict[str, str]:
    if lang == "uk":
        # Gemini sometimes hallucinates Russian spellings in the Ukrainian text
        corrections = {
            "Стрелец": "Стрілець",
            "Телец": "Телець",
            "Близнецы": "Близнюки",
            "Дева": "Діва",
            "Весы": "Терези",
            "Козерог": "Козеріг",
            "Водолей": "Водолій",
            "Рыбы": "Риби"
        }
        for wrong, right in corrections.items():
            block = block.replace(f" {wrong} -", f" {right} -")
            block = block.replace(f" {wrong} —", f" {right} —")

    lines = [line.strip() for line in block.splitlines() if line.strip()]
    full_text = "\n\n".join(lines)
    payload: dict[str, str] = {"all": full_text}

    for key, name in _HOROSCOPE_SIGNS[lang].items():
        matched_line = next((line for line in lines if name in line and (" - " in line or " — " in line)), "")
        payload[key] = matched_line or full_text

    return payload

def _parse_multilang_horoscope(raw_text: str) -> dict[str, dict[str, str]]:
    payload: dict[str, dict[str, str]] = {}
    for lang in _HOROSCOPE_LANGS:
        block = _extract_language_block(raw_text, lang)
        if not block:
            raise ValueError(f"Missing horoscope block for {lang}")
        payload[lang] = _build_language_payload(block, lang)
    return payload


def _parse_batch_horoscope(raw_text: str) -> dict[str, dict[str, dict[str, str]]]:
    # Returns {date_key: payload}
    results: dict[str, dict[str, dict[str, str]]] = {}
    blocks = raw_text.split("DATE:")
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        
        # First line should be the date
        lines = block.splitlines()
        if not lines:
            continue
            
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", lines[0])
        if not date_match:
            continue
        date_key = date_match.group(0)
            
        content = "\n".join(lines[1:])
        
        try:
            payload = _parse_multilang_horoscope(content)
            results[date_key] = payload
        except Exception as exc:
            logging.warning("Failed to parse horoscope block for %s: %s", date_key, exc)
    
    return results

def _build_emergency_horoscope_payload(date_key: str) -> dict[str, dict[str, str]]:
    """Build a complete localized horoscope when the external model is unavailable."""
    date_seed = int(date_key.replace("-", ""))
    payload: dict[str, dict[str, str]] = {}

    for lang in _HOROSCOPE_LANGS:
        templates = _EMERGENCY_HOROSCOPE_TEMPLATES[lang]
        language_payload: dict[str, str] = {}
        lines: list[str] = []
        for index, (sign_key, sign_name) in enumerate(_HOROSCOPE_SIGNS[lang].items()):
            advice = templates[(date_seed + index) % len(templates)]
            line = f"{_ZODIAC_EMOJIS[sign_key]} {sign_name} \u2014 {advice}"
            language_payload[sign_key] = line
            lines.append(line)

        language_payload["all"] = "\n\n".join(lines)
        payload[lang] = language_payload

    return payload



async def _get_or_generate_horoscope_payload(
    db: firestore.Client,
    tarot_model: Any,
    date_key: str,
    fallback_model: Any | None = None,
    bot: Bot | None = None,
) -> dict[str, dict[str, str]] | None:
    # Attempt to get from cache first
    try:
        cached = await _get_cached_horoscope_payload(db, date_key)
    except Exception as exc:
        logging.warning(
            "HOROSCOPE_CACHE_READ_FAILED date_key=%s error_type=%s error=%s",
            date_key,
            type(exc).__name__,
            exc,
        )
        return None
    if cached:
        return cached

    # Generate only the requested day to keep Gemini response size and memory bounded.
    logging.info("Generating batch horoscopes starting from %s", date_key)
    
    start_dt = datetime.strptime(date_key, "%Y-%m-%d")
    batch_configs = []
    for i in range(_HOROSCOPE_BATCH_DAYS):
        target_dt = start_dt + timedelta(days=i)
        t_key = target_dt.strftime("%Y-%m-%d")
        # Check if already cached (optional but good for efficiency)
        if i > 0:
            try:
                existing = await _get_cached_horoscope_payload(db, t_key)
            except Exception as exc:
                logging.warning(
                    "HOROSCOPE_CACHE_READ_FAILED date_key=%s error_type=%s error=%s",
                    t_key,
                    type(exc).__name__,
                    exc,
                )
                return None
            if existing:
                continue
        
        batch_configs.append({
            "date": t_key,
            "theme": _get_daily_theme(t_key)
        })

    if not batch_configs:
        try:
            return await _get_cached_horoscope_payload(db, date_key)
        except Exception as exc:
            logging.warning(
                "HOROSCOPE_CACHE_READ_FAILED date_key=%s error_type=%s error=%s",
                date_key,
                type(exc).__name__,
                exc,
            )
            return None

    model_candidates = [tarot_model]
    if fallback_model is not None and fallback_model is not tarot_model:
        model_candidates.append(fallback_model)
    today_config = next(config for config in batch_configs if config["date"] == date_key)

    last_error = ""
    for attempt, delay_seconds in enumerate(_GENERATION_RETRY_DELAYS, start=1):
        if delay_seconds:
            await asyncio.sleep(delay_seconds)

        model = model_candidates[min(attempt - 1, len(model_candidates) - 1)]
        attempt_configs = batch_configs if attempt == 1 else [today_config]
        prompt = _build_horoscope_prompt(attempt_configs)
        model_name = getattr(model, "model_name", type(model).__name__)
        logging.info(
            "Horoscope generation attempt=%s model=%s dates=%s",
            attempt,
            model_name,
            ",".join(config["date"] for config in attempt_configs),
        )

        try:
            response = await generate_content(model, prompt)
            raw_text = getattr(response, "text", "").strip()
            if not raw_text:
                raise ValueError("Gemini returned empty batch text")

            batch_results = _parse_batch_horoscope(raw_text)
            if not batch_results:
                raise ValueError("Could not parse any dates from batch")
            if date_key not in batch_results:
                raise ValueError(f"Generated batch does not contain current date {date_key}")

            for res_date, res_payload in batch_results.items():
                await _store_cached_horoscope_payload(db, res_date, res_payload)

            return batch_results[date_key]
        except Exception as exc:
            last_error = str(exc)
            logging.error(
                "Batch horoscope generation attempt %s failed model=%s error_type=%s error=%s",
                attempt,
                model_name,
                type(exc).__name__,
                exc,
            )
            await _set_generation_error(db, date_key, last_error, attempt)

            timeout_error = isinstance(exc, asyncio.TimeoutError) or any(
                marker in last_error.lower()
                for marker in ("deadline exceeded", "timed out", "timeout")
            )
            if timeout_error:
                logging.error(
                    "HOROSCOPE_GENERATION_TIMEOUT date_key=%s model=%s; using local fallback",
                    date_key,
                    model_name,
                )
                break

            if "User location is not supported" in last_error:
                logging.error(
                    "GEMINI_LOCATION_UNSUPPORTED date_key=%s model=%s; using local fallback",
                    date_key,
                    model_name,
                )
                break

    payload = _build_emergency_horoscope_payload(date_key)
    logging.warning(
        "HOROSCOPE_LOCAL_FALLBACK_USED date_key=%s last_error=%s",
        date_key,
        last_error,
    )
    try:
        await _store_cached_horoscope_payload(
            db,
            date_key,
            payload,
            source="local_fallback",
        )
    except Exception as exc:
        logging.warning(
            "HOROSCOPE_LOCAL_FALLBACK_CACHE_FAILED date_key=%s error_type=%s error=%s",
            date_key,
            type(exc).__name__,
            exc,
        )
    if bot is not None:
        await _notify_admins_local_horoscope(bot, date_key, last_error)
    return payload


async def send_monthly_card_reminders(bot: Bot, db: firestore.Client):
    logging.info("Starting monthly card reminder broadcast")

    tz = pytz.timezone("Europe/Kyiv")
    now = datetime.now(tz)
    today = now.date()
    month_key = now.strftime("%Y-%m")
    users = await _load_users(db)

    count = 0
    for doc in users:
        user_data = doc.to_dict() or {}
        user_id = doc.id
        lang = user_data.get("language", "uk")

        last_daily_card_date = _parse_date(user_data.get("last_daily_card_date"))
        last_reminder_month = user_data.get("last_monthly_card_reminder_month")

        if not last_daily_card_date:
            continue
        if last_reminder_month == month_key:
            continue

        days_since_last_card = (today - last_daily_card_date.date()).days
        if days_since_last_card < 30:
            continue

        try:
            await bot.send_message(
                chat_id=user_id,
                text=_localized(_MONTHLY_REMINDER_TEXT, lang),
                reply_markup=main_menu_kb(lang),
                parse_mode="HTML",
            )
            await _mark_monthly_reminder_sent(db, user_id, month_key)
            count += 1
            await asyncio.sleep(0.1)
        except TelegramForbiddenError:
            pass
        except Exception as exc:
            logging.error("Monthly reminder send failed for %s: %s", user_id, exc)

    logging.info("Monthly card reminders sent to %s users", count)


async def _send_daily_horoscope(
    bot: Bot,
    db: firestore.Client,
    tarot_model: Any,
    fallback_model: Any | None = None,
):
    logging.info("Starting daily horoscope generation and broadcast")

    tz = pytz.timezone("Europe/Kyiv")
    now = datetime.now(tz)
    
    # Тільки якщо вже пізніше 09:00 ранку
    if now.hour < 9:
        return

    today_date = now.strftime("%d.%m")
    today_key = now.strftime("%Y-%m-%d")


    claimed = await _claim_delivery(db, today_key, now)
    if not claimed:
        logging.info("Daily horoscope delivery already completed or currently locked for %s", today_key)
        return

    count = 0

    try:
        payload = await _get_or_generate_horoscope_payload(
            db,
            tarot_model,
            today_key,
            fallback_model,
            bot,
        )
        if not payload:
            await _mark_delivery_error(db, today_key, "Horoscope payload is unavailable")
            return

        me = await bot.get_me()
        bot_link = f"https://t.me/{me.username}" if me.username else None
        users = await _load_users(db)

        for doc in users:
            user_data = doc.to_dict() or {}
            user_id = doc.id
            lang = user_data.get("language", "uk")
            if lang not in payload:
                lang = "uk"
            if user_data.get("horoscope_enabled", True) is False:
                continue
            if user_data.get("last_horoscope_share_date") == today_key:
                continue

            zodiac_pref = user_data.get("zodiac_sign", "all")
            lang_payload = payload[lang]
            text_to_send = lang_payload.get(zodiac_pref, lang_payload["all"])
            title = _localized(_HOROSCOPE_TITLE, lang).format(date=today_date)
            final_message = f"{title}\n\n{text_to_send}"
            if bot_link:
                final_message = f"{final_message}\n\n{_localized(_HOROSCOPE_SOURCE, lang).format(link=bot_link)}"

            try:
                await bot.send_message(chat_id=user_id, text=final_message, parse_mode="HTML")
                await log_chat_message(db, int(user_id), "bot", final_message)
                await _store_share_text(db, user_id, final_message, today_key)
                await bot.send_message(
                    chat_id=user_id,
                    text=_localized(_HOROSCOPE_FOLLOWUP, lang),
                    reply_markup=main_menu_kb(lang),
                    parse_mode="HTML",
                )
                count += 1
                await asyncio.sleep(0.1)
            except TelegramForbiddenError:
                continue
            except Exception as exc:
                logging.error("Horoscope send failed for %s: %s", user_id, exc)

        await _mark_delivery_completed(db, today_key, count)
    except asyncio.CancelledError:
        try:
            await asyncio.wait_for(
                _mark_delivery_error(db, today_key, "Daily horoscope job timed out"),
                timeout=_FIRESTORE_TIMEOUT_SECONDS + 5,
            )
        except Exception as exc:
            logging.warning(
                "HOROSCOPE_TIMEOUT_UNLOCK_FAILED error_type=%s error=%s",
                type(exc).__name__,
                exc,
            )
        raise
    except Exception as exc:
        await _mark_delivery_error(db, today_key, str(exc))
        raise

    logging.info("Daily horoscope sent to %s users", count)


async def send_daily_horoscope(
    bot: Bot,
    db: firestore.Client,
    tarot_model: Any,
    fallback_model: Any | None = None,
):
    try:
        await asyncio.wait_for(
            _send_daily_horoscope(bot, db, tarot_model, fallback_model),
            timeout=_DAILY_JOB_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logging.error(
            "HOROSCOPE_JOB_TIMEOUT timeout_seconds=%s",
            _DAILY_JOB_TIMEOUT_SECONDS,
        )
    except Exception:
        logging.exception("HOROSCOPE_JOB_FAILED")
