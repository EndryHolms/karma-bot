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


async def send_daily_reminders(bot: Bot, db: firestore.Client):
    logging.info("РџРѕС‡РёРЅР°СЋ СЂРѕР·СЃРёР»РєСѓ РЅР°РіР°РґСѓРІР°РЅСЊ...")
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
                logging.error(f"РџРѕРјРёР»РєР° СЂРѕР·СЃРёР»РєРё РґР»СЏ {user_id}: {e}")

    logging.info(f"РќР°РіР°РґСѓРІР°РЅРЅСЏ СѓСЃРїС–С€РЅРѕ РЅР°РґС–СЃР»Р°РЅРѕ {count} РєРѕСЂРёСЃС‚СѓРІР°С‡Р°Рј.")


async def send_daily_horoscope(bot: Bot, db: firestore.Client, tarot_model):
    logging.info("РџРѕС‡РёРЅР°СЋ РіРµРЅРµСЂР°С†С–СЋ С‚Р° СЂРѕР·СЃРёР»РєСѓ РіРѕСЂРѕСЃРєРѕРїС–РІ...")

    tz = pytz.timezone("Europe/Kyiv")
    today_date = datetime.now(tz).strftime("%d.%m")

    prompt = (
        "РќР°РїРёС€Рё С–СЂРѕРЅС–С‡РЅРёР№, РєСѓРјРµРґРЅРёР№ С‚Р° РґСѓР¶Рµ Р¶РёС‚С‚С”РІРёР№ РіРѕСЂРѕСЃРєРѕРї РЅР° СЃСЊРѕРіРѕРґРЅС– РґР»СЏ РІСЃС–С… 12 Р·РЅР°РєС–РІ Р·РѕРґС–Р°РєСѓ (РїРѕ РѕРґРЅРѕРјСѓ РєРѕСЂРѕС‚РєРѕРјСѓ СЂРµС‡РµРЅРЅСЋ). "
        "РЎС‚РёР»СЊ: СЃР°СЂРєР°Р·Рј, РІС‚РѕРјР° РІС–Рґ СЂРѕР±РѕС‚Рё, Р¶Р°СЂС‚Рё РїСЂРѕ РіСЂРѕС€С–, РїРѕРіРѕРґСѓ С‚Р° СЃС‚РѕСЃСѓРЅРєРё. "
        "РЎРЈР’РћР Рђ РЈРњРћР’Рђ: Р–РѕРґРЅРѕРіРѕ С‚РµРєСЃС‚Сѓ РґРѕ С‡Рё РїС–СЃР»СЏ Р·РЅР°РєС–РІ! Р‘РµР· РІСЃС‚СѓРїС–РІ, Р±РµР· РІРёСЃРЅРѕРІРєС–РІ, Р±РµР· Р·С–СЂРѕС‡РѕРє Markdown. "
        "РўС–Р»СЊРєРё 12 СЂСЏРґРєС–РІ. РћР±РѕРІ'СЏР·РєРѕРІРѕ СЂРѕР±Рё РїРѕСЂРѕР¶РЅС–Р№ СЂСЏРґРѕРє (Enter) РјС–Р¶ Р·РЅР°РєР°РјРё. "
        "Р¤РѕСЂРјР°С‚ РјР°С” Р±СѓС‚Рё С‚РѕС‡РЅРѕ С‚Р°РєРёРј:\n"
        "♈ Овен - [твій жарт]\n\n"
        "♉ Телець - [твій жарт]\n\n"
        "...і так для всіх 12 знаків."
    )

    try:
        response = await asyncio.to_thread(tarot_model.generate_content, prompt)
        raw_text = getattr(response, "text", "").strip()
    except Exception as e:
        logging.error(f"РџРѕРјРёР»РєР° РіРµРЅРµСЂР°С†С–С— РіРѕСЂРѕСЃРєРѕРїСѓ: {e}")
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
        "capricorn": "Козер",
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
            await bot.send_message(
                chat_id=user_id,
                text=_localized(_HOROSCOPE_FOLLOWUP, lang),
                reply_markup=horoscope_share_menu_kb(lang),
                parse_mode="HTML",
            )
            count += 1
            await asyncio.sleep(0.1)
        except Exception:
            pass

    logging.info(f"Р“РѕСЂРѕСЃРєРѕРї СѓСЃРїС–С€РЅРѕ РЅР°РґС–СЃР»Р°РЅРѕ {count} РєРѕСЂРёСЃС‚СѓРІР°С‡Р°Рј.")
