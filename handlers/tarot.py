from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime
from typing import Any

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from firebase_admin import firestore

from firebase_db import (
    REFERRAL_DAILY_BONUS,
    InsufficientBalanceError,
    ensure_user,
    get_balance,
    get_user_language,
    grant_referral_bonus_for_daily_card,
    increment_balance,
)
from handlers.payment import send_stars_invoice
from keyboards import CB_CAREER, CB_DAILY, CB_RELATIONSHIP, back_to_menu_kb, main_menu_kb
from lexicon import get_text

router = Router()

RELATIONSHIP_PRICE = 1
CAREER_PRICE = 1

_admin_env = os.getenv("ADMIN_IDS", "469764985")
ADMIN_IDS = [int(x.strip()) for x in _admin_env.split(",") if x.strip().isdigit()]

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

IMAGES_DAILY = {
    "uk": "https://i.postimg.cc/FHKrfNp0/b_A_richly_detailed_Ta_1.png",
    "en": "https://i.postimg.cc/jS1x5Z4t/b_A_richly_detailed_Ta_1_en.png",
    "ru": "https://i.postimg.cc/FHKrfNp0/b_A_richly_detailed_Ta_1.png",
}

IMAGES_LOVE = {
    "uk": "https://i.postimg.cc/xTZP1Png/b_A_richly_detailed_Ta_2.png",
    "en": "https://i.postimg.cc/wMFHdVjn/b_A_richly_detailed_Ta_2_en.png",
    "ru": "https://i.postimg.cc/nrTZtkh6/b_A_richly_detailed_Ta_2_ru.png",
}

IMAGES_CAREER = {
    "uk": "https://i.postimg.cc/pdfQkb8Z/b_A_richly_detailed_Ta_3.png",
    "en": "https://i.postimg.cc/nzGfvkBT/b_A_richly_detailed_Ta_3_en.png",
    "ru": "https://i.postimg.cc/rmN2SJxQ/b_A_richly_detailed_Ta_3_ru.png",
}

_REFERRAL_BONUS_NOTICE = {
    "uk": "рџЋЃ <b>Р‘РѕРЅСѓСЃ Р·Р° РґСЂСѓРіР°!</b> РўРІС–Р№ РґСЂСѓРі РІС–РґРєСЂРёРІ СЃРІРѕСЋ РїРµСЂС€Сѓ РљР°СЂС‚Сѓ Р”РЅСЏ, С‚РѕР¶ С‚Рё РѕС‚СЂРёРјР°РІ <b>{bonus} в­ђ</b>.",
    "en": "рџЋЃ <b>Friend bonus!</b> Your friend opened their first Card of the Day, so you received <b>{bonus} в­ђ</b>.",
    "ru": "рџЋЃ <b>Р‘РѕРЅСѓСЃ Р·Р° РґСЂСѓРіР°!</b> РўРІРѕР№ РґСЂСѓРі РѕС‚РєСЂС‹Р» СЃРІРѕСЋ РїРµСЂРІСѓСЋ РљР°СЂС‚Сѓ Р”РЅСЏ, РїРѕСЌС‚РѕРјСѓ С‚С‹ РїРѕР»СѓС‡РёР» <b>{bonus} в­ђ</b>.",
}


HEADING_GUIDE = {
    "uk": {
        "cards": "Р С™Р В°РЎР‚РЎвЂљР С‘",
        "reading": "Р СћР Р†РЎвЂ“Р в„– РЎР‚Р С•Р В·Р С”Р В»Р В°Р Т‘",
        "advice": "Р СџР С•РЎР‚Р В°Р Т‘Р В° Р Р†РЎвЂ“Р Т‘ Karma",
        "affirmation": "Р С’РЎвЂћРЎвЂ“РЎР‚Р СР В°РЎвЂ РЎвЂ“РЎРЏ",
    },
    "en": {
        "cards": "Cards",
        "reading": "Your reading",
        "advice": "Advice from Karma",
        "affirmation": "Affirmation",
    },
    "ru": {
        "cards": "Р С™Р В°РЎР‚РЎвЂљРЎвЂ№",
        "reading": "Р СћР Р†Р С•Р в„– РЎР‚Р В°РЎРѓР С”Р В»Р В°Р Т‘",
        "advice": "Р РЋР С•Р Р†Р ВµРЎвЂљ Р С•РЎвЂљ Karma",
        "affirmation": "Р С’РЎвЂћРЎвЂћР С‘РЎР‚Р СР В°РЎвЂ Р С‘РЎРЏ",
    },
}


class ReadingStates(StatesGroup):
    waiting_for_context = State()


def _heading_guide(lang: str) -> dict[str, str]:
    return HEADING_GUIDE.get(lang, HEADING_GUIDE["uk"])


def _tarot_format_prompt(lang: str, target_language: str) -> str:
    headings = _heading_guide(lang)
    return (
        f"Write the entire response only in {target_language}. Do not mix languages. "
        f"Use Telegram HTML only. Do not use Markdown. "
        f"Keep the emojis exactly as shown. Keep exactly one empty line after each heading and one empty line between blocks. "
        f"Return the answer in exactly this structure:\n\n"
        f"СЂСџР‹Т‘ <b>{headings['cards']}:</b>\n\n"
        f"[text]\n\n"
        f"СЂСџвЂРѓ <b>{headings['reading']}:</b>\n\n"
        f"[text]\n\n"
        f"РІСљРЃ <b>{headings['advice']}:</b>\n\n"
        f"[text]\n\n"
        f"СЂСџРЉРЉ <b>{headings['affirmation']}:</b>\n\n"
        f"[text]\n\n"
        f"The affirmation must also be fully in {target_language}."
    )


async def _gemini_generate_text(model: Any, prompt: str) -> str:
    def _call_sync() -> str:
        try:
            resp = model.generate_content(prompt, safety_settings=SAFETY_SETTINGS)
            if not resp or not hasattr(resp, "candidates") or not resp.candidates:
                return ""
            return resp.text.strip()
        except Exception as e:
            print(f"GenAI Text Error: {e}")
            return ""

    return await asyncio.to_thread(_call_sync)


async def _gemini_generate_with_audio(model: Any, prompt: str, audio_bytes: bytes) -> str:
    def _call_sync() -> str:
        fd, path = tempfile.mkstemp(suffix=".ogg")
        os.close(fd)
        try:
            with open(path, "wb") as f:
                f.write(audio_bytes)
            uploaded = genai.upload_file(path)
            resp = model.generate_content([prompt, uploaded], safety_settings=SAFETY_SETTINGS)
            return resp.text.strip() if resp else ""
        except Exception as e:
            print(f"GenAI Audio Error: {e}")
            return ""
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    return await asyncio.to_thread(_call_sync)


async def _send_long(message: Message, text: str, reply_markup: Any = None, lang: str = "uk") -> None:
    limit = 4000
    chunks = [text[i : i + limit] for i in range(0, len(text), limit)] or [text]

    for chunk in chunks[:-1]:
        await message.answer(chunk, parse_mode="HTML")

    await message.answer(
        chunks[-1],
        reply_markup=reply_markup,
        parse_mode="HTML",
    )


async def _start_paid_reading(
    callback: CallbackQuery,
    state: FSMContext,
    db: firestore.Client,
    *,
    reading_key: str,
    price: int,
    prompt_key: str,
) -> None:
    if not callback.from_user:
        return

    await ensure_user(
        db,
        user_id=callback.from_user.id,
        username=callback.from_user.username or "",
        first_name=callback.from_user.first_name or "",
    )
    await callback.answer()

    lang = await get_user_language(db, callback.from_user.id)
    is_admin = callback.from_user.id in ADMIN_IDS

    if not is_admin:
        balance = await get_balance(db, callback.from_user.id)
        if balance < price:
            title_key = "invoice_love_title" if reading_key == "relationship" else "invoice_career_title"
            desc_key = "invoice_love_desc" if reading_key == "relationship" else "invoice_career_desc"
            await send_stars_invoice(
                callback=callback,
                title=get_text(lang, title_key),
                description=get_text(lang, desc_key),
                amount_stars=price,
                payload=f"topup:{price}",
            )
            return

        try:
            await increment_balance(db, callback.from_user.id, -price)
        except InsufficientBalanceError:
            if callback.message:
                await callback.message.answer(get_text(lang, "error_payment"))
            return

    await state.set_state(ReadingStates.waiting_for_context)
    await state.update_data(reading_key=reading_key, price=price)

    if callback.message:
        await callback.message.answer(
            get_text(lang, prompt_key),
            reply_markup=back_to_menu_kb(lang),
            parse_mode="HTML",
        )


@router.callback_query(F.data == CB_DAILY)
async def daily_card(callback: CallbackQuery, db: firestore.Client, tarot_model: Any) -> None:
    if not callback.from_user:
        return
    user_id = str(callback.from_user.id)
    await ensure_user(
        db,
        user_id=callback.from_user.id,
        username=callback.from_user.username or "",
        first_name=callback.from_user.first_name or "",
    )

    lang = await get_user_language(db, callback.from_user.id)
    today_str = datetime.now().strftime("%Y-%m-%d")

    is_admin = callback.from_user.id in ADMIN_IDS
    if not is_admin:
        doc = db.collection("users").document(user_id).get()
        user_data = doc.to_dict() or {}
        if user_data.get("last_daily_card_date") == today_str:
            await callback.answer(get_text(lang, "daily_already_opened"), show_alert=True)
            return

    await callback.answer()

    ai_languages = {"uk": "Ukrainian", "en": "English", "ru": "Russian"}
    target_language = ai_languages.get(lang, "Ukrainian")
    prompt = (
        "Draw a card of the day and explain the energy of this day. "
        + _tarot_format_prompt(lang, target_language)
    )

    ai_task = asyncio.create_task(_gemini_generate_text(tarot_model, prompt))

    msg = await callback.message.answer(get_text(lang, "loading_daily_1"), parse_mode="HTML")
    await asyncio.sleep(1.5)
    await msg.edit_text(get_text(lang, "loading_daily_2"), parse_mode="HTML")
    await asyncio.sleep(1.5)
    await msg.edit_text(get_text(lang, "loading_daily_3"), parse_mode="HTML")

    referral_bonus_granted_to = None
    try:
        text = await ai_task
        if text:
            db.collection("users").document(user_id).update({"last_daily_card_date": today_str})
            if not is_admin:
                referral_bonus_granted_to = await grant_referral_bonus_for_daily_card(
                    db,
                    callback.from_user.id,
                    REFERRAL_DAILY_BONUS,
                )

        await msg.delete()

        if text:
            current_img = IMAGES_DAILY.get(lang, IMAGES_DAILY["uk"])
            await callback.message.answer_photo(photo=current_img)
            content_text = f"{get_text(lang, 'daily_energy_here')}\n\n{text}"
            await _send_long(callback.message, content_text, reply_markup=main_menu_kb(lang), lang=lang)

            if referral_bonus_granted_to:
                ref_lang = await get_user_language(db, referral_bonus_granted_to)
                notice = _REFERRAL_BONUS_NOTICE.get(ref_lang, _REFERRAL_BONUS_NOTICE["uk"]).format(
                    bonus=REFERRAL_DAILY_BONUS
                )
                try:
                    await callback.bot.send_message(referral_bonus_granted_to, notice, parse_mode="HTML")
                except Exception:
                    pass
        else:
            await callback.message.answer(get_text(lang, "error_generate"), reply_markup=main_menu_kb(lang))
    except Exception as e:
        print(f"Daily Handler Error: {e}")
        try:
            await msg.delete()
        except Exception:
            pass
        await callback.message.answer(get_text(lang, "error_generate"), reply_markup=main_menu_kb(lang))


@router.callback_query(F.data == CB_RELATIONSHIP)
async def relationship_reading(callback: CallbackQuery, state: FSMContext, db: firestore.Client) -> None:
    await _start_paid_reading(
        callback,
        state,
        db,
        reading_key="relationship",
        price=RELATIONSHIP_PRICE,
        prompt_key="ask_love_context",
    )


@router.callback_query(F.data == CB_CAREER)
async def career_reading(callback: CallbackQuery, state: FSMContext, db: firestore.Client) -> None:
    await _start_paid_reading(
        callback,
        state,
        db,
        reading_key="career",
        price=CAREER_PRICE,
        prompt_key="ask_career_context",
    )


@router.message(ReadingStates.waiting_for_context)
async def reading_context_message(message: Message, state: FSMContext, db: firestore.Client, bot: Any, tarot_model: Any) -> None:
    if not message.from_user:
        return
    lang = await get_user_language(db, message.from_user.id)

    data = await state.get_data()
    reading_key = data.get("reading_key")
    price = data.get("price", 1)

    topic_by_lang = {
        "uk": {"relationship": "РЎРѓРЎвЂљР С•РЎРѓРЎС“Р Р…Р С”Р С‘", "career": "Р С”Р В°РЎР‚'РЎвЂќРЎР‚Р В°"},
        "en": {"relationship": "relationships", "career": "career"},
        "ru": {"relationship": "Р С•РЎвЂљР Р…Р С•РЎв‚¬Р ВµР Р…Р С‘РЎРЏ", "career": "Р С”Р В°РЎР‚РЎРЉР ВµРЎР‚Р В°"},
    }
    topic = topic_by_lang.get(lang, topic_by_lang["uk"]).get(reading_key, topic_by_lang["uk"]["career"])
    wait_text = get_text(lang, "loading_love_cards") if reading_key == "relationship" else get_text(lang, "loading_cards")
    msg = await message.answer(wait_text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")

    ai_languages = {"uk": "Ukrainian", "en": "English", "ru": "Russian"}
    target_language = ai_languages.get(lang, "Ukrainian")
    format_prompt = _tarot_format_prompt(lang, target_language)

    text = ""
    try:
        if message.voice:
            file_info = await bot.get_file(message.voice.file_id)
            audio_bytes = (await bot.download_file(file_info.file_path)).read()
            prompt = (
                f"The user sent voice context about {topic}. Create a tarot reading. "
                + format_prompt
            )
            text = await _gemini_generate_with_audio(tarot_model, prompt, audio_bytes)
        else:
            user_text = message.text or ""
            prompt = (
                f"The user context about {topic} is: {user_text}. Create a tarot reading. "
                + format_prompt
            )
            text = await _gemini_generate_text(tarot_model, prompt)
    except Exception as e:
        print(f"Reading Context Error: {e}")

    await msg.delete()

    if not text:
        if message.from_user.id not in ADMIN_IDS:
            try:
                await increment_balance(db, message.from_user.id, price)
                refund_note = get_text(lang, "refund_note_balance").format(price=price)
            except Exception:
                refund_note = ""
        else:
            refund_note = ""

        await message.answer(
            get_text(lang, "magic_interrupted").format(refund_note=refund_note),
            reply_markup=main_menu_kb(lang),
            parse_mode="HTML",
        )
        await state.clear()
        return

    img_dict = IMAGES_LOVE if reading_key == "relationship" else IMAGES_CAREER
    img_to_send = img_dict.get(lang, img_dict["uk"])

    await message.answer_photo(photo=img_to_send)
    content_text = f"{get_text(lang, 'cards_on_table')}\n\n{text}"
    await _send_long(message, content_text, reply_markup=main_menu_kb(lang), lang=lang)
    await state.clear()


