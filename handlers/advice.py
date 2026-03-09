from __future__ import annotations
import asyncio
import os
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from firebase_admin import firestore

# 👇 Наші нові імпорти
from firebase_db import InsufficientBalanceError, ensure_user, get_balance, increment_balance, get_user_language
from lexicon import get_text
from handlers.payment import send_stars_invoice
from keyboards import CB_ADVICE, back_to_menu_kb, main_menu_kb

router = Router()

ADVICE_PRICE = 1

# Мультимовні картинки для Поради Всесвіту
IMAGES_ADVICE = {
    "uk": "https://i.postimg.cc/qvxpMPwf/b-A-richly-detailed-Ta-4.png",
    "en": "https://i.postimg.cc/vBtwWzf0/b_A_richly_detailed_Ta_4_en.png", # 👈 Встав посилання
    "ru": "https://i.postimg.cc/MTmJyDVs/b_A_richly_detailed_Ta_4_ru.png"  # 👈 Встав посилання
}
_admin_env = os.getenv("ADMIN_IDS", "469764985") 
ADMIN_IDS = [int(x.strip()) for x in _admin_env.split(",") if x.strip().isdigit()]

class AdviceStates(StatesGroup):
    waiting_for_question = State()

async def _gemini_text(model: Any, prompt: str) -> str:
    def _sync():
        try:
            resp = model.generate_content(prompt)
            return (getattr(resp, "text", "") or "").strip()
        except Exception as e:
            print(f"Advice Gen Error: {e}")
            return ""
    return await asyncio.to_thread(_sync)

@router.callback_query(F.data == CB_ADVICE)
async def ask_advice_start(callback: CallbackQuery, state: FSMContext, db: firestore.Client) -> None:
    if not callback.from_user: return
    await ensure_user(
        db, 
        user_id=callback.from_user.id, 
        username=callback.from_user.username or "", 
        first_name=callback.from_user.first_name or ""
    )
    await callback.answer()

    # Отримуємо мову користувача
    lang = await get_user_language(db, callback.from_user.id)
    is_admin = callback.from_user.id in ADMIN_IDS

    if not is_admin:
        balance = await get_balance(db, callback.from_user.id)
        if balance < ADVICE_PRICE:
            await send_stars_invoice(
                callback=callback,
                title=get_text(lang, "invoice_advice_title"),
                description=get_text(lang, "invoice_advice_desc"),
                amount_stars=ADVICE_PRICE,
                payload=f"topup:{ADVICE_PRICE}"
            )
            return
        
        try:
            await increment_balance(db, callback.from_user.id, -ADVICE_PRICE)
        except InsufficientBalanceError:
            if callback.message:
                await callback.message.answer(get_text(lang, "error_payment"))
            return

    await state.set_state(AdviceStates.waiting_for_question)
    await state.update_data(price=ADVICE_PRICE)
    
    if callback.message:
        await callback.message.answer(
            get_text(lang, "ask_question"),
            reply_markup=back_to_menu_kb(lang)
        )

@router.message(AdviceStates.waiting_for_question)
async def advice_process(message: Message, state: FSMContext, advice_model: Any, db: firestore.Client) -> None:
    if not message.from_user: return
    
    # Отримуємо мову
    lang = await get_user_language(db, message.from_user.id)
    
    user_text = message.text or get_text(lang, "default_advice_request")
    
    data = await state.get_data()
    price = data.get("price", 1)

    # Перекладений текст завантаження
    msg = await message.answer(get_text(lang, "loading_advice"), reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    
    # ВКАЗІВКА ДЛЯ GEMINI ЯКОЮ МОВОЮ ВІДПОВІДАТИ
    ai_languages = {"uk": "Ukrainian", "en": "English", "ru": "Russian"}
    target_language = ai_languages.get(lang, "Ukrainian")
    
    # 👇 Жорстка вказівка перекладати всі заголовки та текст
    prompt = f"Користувач запитує: '{user_text}'. Дай глибоку, філософську, але практичну пораду. Використовуй емодзі.\n\nIMPORTANT: You MUST write your ENTIRE response (including ALL structured headings or quotes) exclusively in {target_language} language!"
    
    await msg.delete()

    if not text:
        is_admin = message.from_user.id in ADMIN_IDS
        refund_note = ""
        if not is_admin:
            try:
                await increment_balance(db, message.from_user.id, price)
                refund_note = get_text(lang, "refund_note").format(price=price)
            except: pass
        
        # Перекладене повідомлення про помилку + повернення коштів
        silent_msg = get_text(lang, "universe_silent")
        await message.answer(f"{silent_msg} {refund_note}".strip(), reply_markup=main_menu_kb(lang), parse_mode="HTML")
        await state.clear()
        return

# Відправка правильної картинки залежно від мови та тексту
    current_img = IMAGES_ADVICE.get(lang, IMAGES_ADVICE["uk"])
    await message.answer_photo(photo=current_img, caption=get_text(lang, "universe_answer"), parse_mode="HTML")
    
    await message.answer(text, parse_mode="HTML")
    
    # Відправляємо меню
    await message.answer(get_text(lang, "more_action_btn"), reply_markup=main_menu_kb(lang), parse_mode="HTML")
    await state.clear()