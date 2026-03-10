import asyncio
import logging
from datetime import datetime

import pytz
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from firebase_admin import firestore

from keyboards import horoscope_share_menu_kb, main_menu_kb

_DAILY_REMINDER_TEXT = {
    "uk": "✨ <i>Всесвіт має для тебе послання...</i>\n\nТвоя Карта Дня на сьогодні ще не відкрита. Дізнайся, які енергії тебе оточують просто зараз 👇",
    "en": "✨ <i>The Universe has a message for you...</i>\n\nYour Card of the Day is still unopened. Find out what energies are surrounding you right now 👇",
    "ru": "✨ <i>У Вселенной есть для тебя послание...</i>\n\nТвоя Карта Дня на сегодня еще не открыта. Узнай, какие энергии окружают тебя прямо сейчас 👇",
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


def _localized(mapping: dict[str, str], lang: str) -> str:
    return mapping.get(lang, mapping["uk"])


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


async def send_daily_reminders(bot: Bot, db: firestore.Client):
    logging.info("Starting daily reminders broadcast")
    today_str = datetime.now().strftime("%Y-%m-%d")
    users_ref = db.collection("users").stream()

    count = 0
    for doc in users_ref:
        user_data = doc.to_dict() or {}
        user_id = doc.id
        last_date = user_data.get("last_daily_card_date")
        lang = user_data.get("language", "uk")

        if last_date != today_str:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=_localized(_DAILY_REMINDER_TEXT, lang),
                    reply_markup=main_menu_kb(lang),
                    parse_mode="HTML",
                )
                count += 1
                await asyncio.sleep(0.1)
            except TelegramForbiddenError:
                pass
            except Exception as e:
                logging.error("Reminder send failed for %s: %s", user_id, e)

    logging.info("Daily reminders sent to %s users", count)


async def send_daily_horoscope(bot: Bot, db: firestore.Client, tarot_model):
    logging.info("Starting daily horoscope generation and broadcast")

    tz = pytz.timezone("Europe/Kyiv")
    now = datetime.now(tz)
    today_date = now.strftime("%d.%m")
    today_key = now.strftime("%Y-%m-%d")

    prompt = (
        "Напиши іронічний, кумедний та дуже життєвий гороскоп на сьогодні для всіх 12 знаків зодіаку (по одному короткому реченню). "
        "Стиль: сарказм, іронія від роботи, жарти про гроші, погоду та стосунки. "
        "СУВОРА УМОВА: Жодного тексту до чи після знаків. Без вступів, без висновків, без зірочок Markdown. "
        "Тільки 12 рядків. Обов'язково роби порожній рядок (Enter) між знаками. "
        "Формат має бути точно таким:\n"
        "♈ Овен - [твій жарт]\n\n"
        "♉ Телець - [твій жарт]\n\n"
        "...і так для всіх 12 знаків."
    )

    try:
        response = await asyncio.to_thread(tarot_model.generate_content, prompt)
        raw_text = getattr(response, "text", "").strip()
    except Exception as e:
        logging.error("Horoscope generation failed: %s", e)
        return

    if not raw_text:
        return

    signs_mapping = {
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
    }

    user_horoscopes = {"all": raw_text}
    lines = raw_text.split("\n")
    for key, name in signs_mapping.items():
        sign_line = ""
        for line in lines:
            if name in line and ("-" in line or "—" in line):
                sign_line = line.strip()
                break
        user_horoscopes[key] = sign_line if sign_line else raw_text

    users_ref = db.collection("users").stream()
    count = 0

    for doc in users_ref:
        user_data = doc.to_dict() or {}
        user_id = doc.id
        lang = user_data.get("language", "uk")
        zodiac_pref = user_data.get("zodiac_sign", "all")
        text_to_send = user_horoscopes.get(zodiac_pref, user_horoscopes["all"])
        title = _localized(_HOROSCOPE_TITLE, lang).format(date=today_date)
        final_message = f"{title}\n\n{text_to_send}"

        try:
            await bot.send_message(chat_id=user_id, text=final_message, parse_mode="HTML")
            await _store_share_text(db, user_id, final_message, today_key)
            await bot.send_message(
                chat_id=user_id,
                text=_localized(_HOROSCOPE_FOLLOWUP, lang),
                reply_markup=horoscope_share_menu_kb(lang),
                parse_mode="HTML",
            )
            count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logging.error("Horoscope send failed for %s: %s", user_id, e)

    logging.info("Daily horoscope sent to %s users", count)