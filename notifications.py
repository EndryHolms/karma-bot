import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import pytz
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from firebase_admin import firestore

from firebase_db import log_chat_message
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
_GENERATION_RETRY_DELAYS = (0, 30, 90)
_DELIVERY_LOCK_STALE_MINUTES = 180

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
        snap = _daily_horoscope_doc(db, date_key).get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        payload = data.get("payload")
        return payload if isinstance(payload, dict) else None

    return await asyncio.to_thread(_read_sync)


async def _store_cached_horoscope_payload(db: firestore.Client, date_key: str, payload: dict[str, dict[str, str]]) -> None:
    def _write_sync() -> None:
        _daily_horoscope_doc(db, date_key).set(
            {
                "payload": payload,
                "created_at": firestore.SERVER_TIMESTAMP,
                "generation_error": firestore.DELETE_FIELD,
            },
            merge=True,
        )

    await asyncio.to_thread(_write_sync)


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

    await asyncio.to_thread(_write_sync)


async def _claim_delivery(db: firestore.Client, date_key: str, now: datetime) -> bool:
    def _tx_sync() -> bool:
        ref = _daily_horoscope_doc(db, date_key)
        now_iso = now.isoformat()
        stale_before_iso = (now - timedelta(minutes=_DELIVERY_LOCK_STALE_MINUTES)).isoformat()

        @firestore.transactional
        def _run(transaction: firestore.Transaction) -> bool:
            snap = ref.get(transaction=transaction)
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
            },
            merge=True,
        )

    await asyncio.to_thread(_write_sync)


async def _mark_delivery_error(db: firestore.Client, date_key: str, message: str) -> None:
    def _write_sync() -> None:
        _daily_horoscope_doc(db, date_key).set(
            {
                "delivery_error": message,
                "delivery_failed_at": datetime.utcnow().isoformat(),
            },
            merge=True,
        )

    await asyncio.to_thread(_write_sync)


def _build_horoscope_prompt(day_configs: list[dict[str, str]]) -> str:
    # day_configs contains list of {"date": "YYYY-MM-DD", "theme": "...", "label": "DD.MM"}
    requests_str = "\n".join([f"DATE:{c['date']} | THEME: {c['theme']}" for c in day_configs])
    
    return (
        f"Generate daily horoscopes for the following dates and themes:\n{requests_str}\n\n"
        f"For EACH date, provide 3 sections: LANG:uk, LANG:en, LANG:ru. "
        f"Tone: witty, ironic, life-like, with sharp sarcasm. Use unexpected metaphors. "
        f"IMPORTANT: Avoid boring zodiac clichés! Leo is NOT just about royalty/crowns. "
        f"Taurus is NOT just about being stubborn. Pisces is NOT just about dreams. "
        f"Describe their day using mundane objects (cold coffee, Wi-Fi signals, broken zippers, IKEA furniture, tax reports). "
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
            block = block.replace(wrong, right)

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
            
        date_key = lines[0].strip()
        # Basic date format check YYYY-MM-DD
        if len(date_key) < 10 or "-" not in date_key:
            continue
            
        content = "\n".join(lines[1:])
        
        try:
            payload = _parse_multilang_horoscope(content)
            results[date_key] = payload
        except Exception as exc:
            logging.warning("Failed to parse horoscope block for %s: %s", date_key, exc)
    
    return results


async def _get_or_generate_horoscope_payload(db: firestore.Client, tarot_model: Any, date_key: str) -> dict[str, dict[str, str]] | None:
    # Attempt to get from cache first
    cached = await _get_cached_horoscope_payload(db, date_key)
    if cached:
        return cached

    # Not in cache, let's generate a batch of 7 days starting from today to save credits
    logging.info("Generating batch horoscopes starting from %s", date_key)
    
    start_dt = datetime.strptime(date_key, "%Y-%m-%d")
    batch_configs = []
    for i in range(7):
        target_dt = start_dt + timedelta(days=i)
        t_key = target_dt.strftime("%Y-%m-%d")
        # Check if already cached (optional but good for efficiency)
        if i > 0:
            existing = await _get_cached_horoscope_payload(db, t_key)
            if existing:
                continue
        
        batch_configs.append({
            "date": t_key,
            "theme": _get_daily_theme(t_key)
        })

    if not batch_configs:
        return await _get_cached_horoscope_payload(db, date_key)

    prompt = _build_horoscope_prompt(batch_configs)
    
    last_error = ""
    for attempt, delay_seconds in enumerate(_GENERATION_RETRY_DELAYS, start=1):
        if delay_seconds:
            await asyncio.sleep(delay_seconds)

        try:
            response = await asyncio.to_thread(tarot_model.generate_content, prompt)
            raw_text = getattr(response, "text", "").strip()
            if not raw_text:
                raise ValueError("Gemini returned empty batch text")

            batch_results = _parse_batch_horoscope(raw_text)
            if not batch_results:
                raise ValueError("Could not parse any dates from batch")

            for res_date, res_payload in batch_results.items():
                await _store_cached_horoscope_payload(db, res_date, res_payload)
            
            return batch_results.get(date_key)
        except Exception as exc:
            last_error = str(exc)
            logging.error("Batch horoscope generation attempt %s failed: %s", attempt, exc)
            await _set_generation_error(db, date_key, last_error, attempt)

    return None


async def send_monthly_card_reminders(bot: Bot, db: firestore.Client):
    logging.info("Starting monthly card reminder broadcast")

    tz = pytz.timezone("Europe/Kyiv")
    now = datetime.now(tz)
    today = now.date()
    month_key = now.strftime("%Y-%m")
    users_ref = db.collection("users").stream()

    count = 0
    for doc in users_ref:
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


async def send_daily_horoscope(bot: Bot, db: firestore.Client, tarot_model: Any):
    logging.info("Starting daily horoscope generation and broadcast")

    tz = pytz.timezone("Europe/Kyiv")
    now = datetime.now(tz)
    
    # Тільки якщо вже пізніше 09:00 ранку
    if now.hour < 9:
        return

    today_date = now.strftime("%d.%m")
    today_key = now.strftime("%Y-%m-%d")

    payload = await _get_or_generate_horoscope_payload(db, tarot_model, today_key)
    if not payload:
        return

    claimed = await _claim_delivery(db, today_key, now)
    if not claimed:
        logging.info("Daily horoscope delivery already completed or currently locked for %s", today_key)
        return

    me = await bot.get_me()
    bot_link = f"https://t.me/{me.username}" if me.username else None

    users_ref = db.collection("users").stream()
    count = 0

    try:
        for doc in users_ref:
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
    except Exception as exc:
        await _mark_delivery_error(db, today_key, str(exc))
        raise

    logging.info("Daily horoscope sent to %s users", count)
