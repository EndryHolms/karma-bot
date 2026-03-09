from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime
from typing import Any

import google.generativeai as genai

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from firebase_admin import firestore

# 👇 Наші нові імпорти
from firebase_db import InsufficientBalanceError, ensure_user, get_balance, increment_balance, get_user_language
from lexicon import get_text
from handlers.payment import send_stars_invoice
from keyboards import CB_CAREER, CB_DAILY, CB_RELATIONSHIP, back_to_menu_kb, main_menu_kb

router = Router()

RELATIONSHIP_PRICE = 1
CAREER_PRICE = 1

_admin_env = os.getenv("ADMIN_IDS", "469764985") 
ADMIN_IDS = [int(x.strip()) for x in _admin_env.split(",") if x.strip().isdigit()]

IMAGES_DAILY = {
    "uk": "https://i.postimg.cc/FHKrfNp0/b_A_richly_detailed_Ta_1.png",
    "en": "https://i.postimg.cc/jS1x5Z4t/b-A-richly-detailed-Ta-1-en.png", # 👈 Встав посилання
    "ru": "https://i.postimg.cc/FHKrfNp0/b_A_richly_detailed_Ta_1.png"  # 👈 Встав посилання
}

IMAGES_LOVE = {
    "uk": "https://i.postimg.cc/xTZP1Png/b_A_richly_detailed_Ta_2.png",
    "en": "https://i.postimg.cc/wMFHdVjn/b_A_richly_detailed_Ta_2_en.png",   # 👈 Встав посилання
    "ru": "https://i.postimg.cc/nrTZtkh6/b_A_richly_detailed_Ta_2_ru.png"    # 👈 Встав посилання
}

IMAGES_CAREER = {
    "uk": "https://i.postimg.cc/pdfQkb8Z/b_A_richly_detailed_Ta_3.png",
    "en": "https://i.postimg.cc/nzGfvkBT/b_A_richly_detailed_Ta_3_en.png", # 👈 Встав посилання
    "ru": "https://i.postimg.cc/rmN2SJxQ/b_A_richly_detailed_Ta_3_ru.png"  # 👈 Встав посилання
}

class ReadingStates(StatesGroup):
    waiting_for_context = State()

async def _gemini_generate_text(model: Any, prompt: str) -> str:
    def _call_sync() -> str:
        try:
            resp = model.generate_content(prompt)
            return (getattr(resp, "text", "") or "").strip()
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
            resp = model.generate_content([prompt, uploaded])
            return (getattr(resp, "text", "") or "").strip()
        except Exception as e:
            print(f"GenAI Audio Error: {e}")
            return ""
        finally:
            try: os.remove(path)
            except OSError: pass
    return await asyncio.to_thread(_call_sync)

async def _send_long(message: Message, text: str, reply_markup: Any = None, lang: str = "uk") -> None:
    limit = 4000
    chunks = [text[i : i + limit] for i in range(0, len(text), limit)]
    for chunk in chunks:
        await message.answer(chunk)
        
    if reply_markup:
        await message.answer(
            get_text(lang, "more_action_btn"), 
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

@router.callback_query(F.data == CB_DAILY)
async def daily_card(callback: CallbackQuery, db: firestore.Client, tarot_model: Any) -> None:
    if not callback.from_user: return
    user_id = str(callback.from_user.id)
    await ensure_user(db, user_id=callback.from_user.id, username=callback.from_user.username or "", first_name=callback.from_user.first_name or "")
    
    # Визначаємо мову
    lang = await get_user_language(db, callback.from_user.id)

    is_admin = callback.from_user.id in ADMIN_IDS
    if not is_admin:
        today_str = datetime.now().strftime("%Y-%m-%d")
        doc = db.collection("users").document(user_id).get()
        user_data = doc.to_dict() or {}
        if user_data.get("last_daily_card_date") == today_str:
            await callback.answer(get_text(lang, "daily_already_opened"), show_alert=True)
            return

    await callback.answer()
    
    msg = await callback.message.answer(get_text(lang, "loading_daily_1"), parse_mode="HTML")
    await asyncio.sleep(2.0)
    await msg.edit_text(get_text(lang, "loading_daily_2"), parse_mode="HTML")
    await asyncio.sleep(2.0)
    await msg.edit_text(get_text(lang, "loading_daily_3"), parse_mode="HTML")
    
    ai_languages = {"uk": "Ukrainian", "en": "English", "ru": "Russian"}
    target_language = ai_languages.get(lang, "Ukrainian")
    
   # 👇 Жорстка вказівка перекладати всі заголовки
    prompt = f"Витягни для мене карту дня і поясни енергію цього дня. Виділи афірмацію жирним курсивом і додай смайлик ✨.\n\nIMPORTANT: You MUST write your ENTIRE response (including ALL structured headings like 'Порада від Karma', 'Афірмація', 'Карти', 'Твій розклад') exclusively in {target_language} language!"
    
    try:
        text = await _gemini_generate_text(tarot_model, prompt)
        if text:
            db.collection("users").document(user_id).update({"last_daily_card_date": datetime.now().strftime("%Y-%m-%d")})
        
        await msg.delete()
        
        if callback.message:
            if text:
                # 👇 Беремо правильну картинку для обраної мови
                current_img = IMAGES_DAILY.get(lang, IMAGES_DAILY["uk"])
                await callback.message.answer_photo(photo=current_img, caption=get_text(lang, "daily_energy_here"), parse_mode="HTML")


@router.callback_query(F.data == CB_RELATIONSHIP)
async def relationship_reading(callback: CallbackQuery, state: FSMContext, db: firestore.Client) -> None:
    lang = await get_user_language(db, callback.from_user.id if callback.from_user else 0)
    await _start_paid_reading(
        callback=callback, state=state, db=db, lang=lang,
        price=RELATIONSHIP_PRICE, 
        reading_key="relationship",
        title=get_text(lang, "invoice_love_title"),
        description=get_text(lang, "invoice_love_desc")
    )


@router.callback_query(F.data == CB_CAREER)
async def career_reading(callback: CallbackQuery, state: FSMContext, db: firestore.Client) -> None:
    lang = await get_user_language(db, callback.from_user.id if callback.from_user else 0)
    await _start_paid_reading(
        callback=callback, state=state, db=db, lang=lang,
        price=CAREER_PRICE, 
        reading_key="career",
        title=get_text(lang, "invoice_career_title"),
        description=get_text(lang, "invoice_career_desc")
    )


async def _start_paid_reading(*, callback: CallbackQuery, state: FSMContext, db: firestore.Client, lang: str, price: int, reading_key: str, title: str, description: str) -> None:
    if not callback.from_user: return
    await ensure_user(db, user_id=callback.from_user.id, username=callback.from_user.username or "", first_name=callback.from_user.first_name or "")
    await callback.answer()

    is_admin = callback.from_user.id in ADMIN_IDS
    if is_admin:
        if callback.message: await callback.message.answer("👑 Admin Mode: Payment skipped.")
    else:
        balance = await get_balance(db, callback.from_user.id)
        if balance < price:
            await send_stars_invoice(
                callback=callback, title=title, description=description,
                amount_stars=price, payload=f"topup:{price}"
            )
            return
        try:
            await increment_balance(db, callback.from_user.id, -price)
        except InsufficientBalanceError:
            if callback.message: await callback.message.answer(get_text(lang, "error_payment"))
            return

    await state.set_state(ReadingStates.waiting_for_context)
    await state.update_data(reading_key=reading_key, price=price)
    
    if callback.message:
        if reading_key == "relationship":
            await callback.message.answer(get_text(lang, "ask_love_context"), reply_markup=back_to_menu_kb(lang))
        elif reading_key == "career":
            await callback.message.answer(get_text(lang, "ask_career_context"), reply_markup=back_to_menu_kb(lang))
        else:
            await callback.message.answer(get_text(lang, "ask_general_context"), reply_markup=back_to_menu_kb(lang))


@router.message(ReadingStates.waiting_for_context)
async def reading_context_message(message: Message, state: FSMContext, db: firestore.Client, bot: Any, tarot_model: Any) -> None:
    if not message.from_user: return
    lang = await get_user_language(db, message.from_user.id)
    
    data = await state.get_data()
    reading_key = data.get("reading_key")
    price = data.get("price", 1)
    
    topic = "стосунки" if reading_key == "relationship" else "кар'єра"
    wait_text = get_text(lang, "loading_love_cards") if reading_key == "relationship" else get_text(lang, "loading_cards")
    msg = await message.answer(wait_text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    
    ai_languages = {"uk": "Ukrainian", "en": "English", "ru": "Russian"}
    target_language = ai_languages.get(lang, "Ukrainian")
    
    text = ""
    try:
        if message.voice:
            file_info = await bot.get_file(message.voice.file_id)
            audio_bytes = (await bot.download_file(file_info.file_path)).read()
            prompt = f"Контекст про {topic} (голос). Зроби розклад.\n\nIMPORTANT: You MUST write your ENTIRE response (including ALL structured headings like 'Порада від Karma', 'Афірмація', 'Карти', 'Твій розклад') exclusively in {target_language} language!"
            text = await _gemini_generate_with_audio(tarot_model, prompt, audio_bytes)
        else:
            user_text = message.text or ""
            prompt = f"Контекст про {topic}: {user_text}. Зроби розклад.\n\nIMPORTANT: You MUST write your ENTIRE response (including ALL structured headings like 'Порада від Karma', 'Афірмація', 'Карти', 'Твій розклад') exclusively in {target_language} language!"
            text = await _gemini_generate_text(tarot_model, prompt)
    except Exception as e:
        print(f"Reading Context Error: {e}")

    await msg.delete()
    
    if not text:
        is_admin = message.from_user.id in ADMIN_IDS
        refund_note = ""
        if not is_admin:
            try:
                await increment_balance(db, message.from_user.id, price)
                refund_note = get_text(lang, "refund_note_balance").format(price=price)
            except Exception:
                pass
        
        error_msg = get_text(lang, "magic_interrupted").format(refund_note=refund_note)
        await message.answer(error_msg, reply_markup=main_menu_kb(lang), parse_mode="HTML")
        await state.clear()
        return

    # 👇 Підставляємо правильну картинку з потрібного словника
    img_dict = IMAGES_LOVE if reading_key == "relationship" else IMAGES_CAREER
    img_to_send = img_dict.get(lang, img_dict["uk"])
    
    await message.answer_photo(photo=img_to_send, caption=get_text(lang, "cards_on_table"), parse_mode="HTML")
    await _send_long(message, text, reply_markup=main_menu_kb(lang), lang=lang)
    await state.clear()