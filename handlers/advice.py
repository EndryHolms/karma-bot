from __future__ import annotations

import asyncio
import os
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from firebase_admin import firestore

from firebase_db import InsufficientBalanceError, ensure_user, get_balance, increment_balance
from handlers.payment import send_stars_invoice
from keyboards import CB_ADVICE, back_to_menu_kb, main_menu_kb

router = Router()

ADVICE_PRICE = 1
IMG_ADVICE = "https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=800&q=80" # Космос/зірки

# Адміни з змінних оточення
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
    await ensure_user(db, callback.from_user.id, callback.from_user.username or "", callback.from_user.first_name or "")
    await callback.answer()

    is_admin = callback.from_user.id in ADMIN_IDS

    if not is_admin:
        balance = await get_balance(db, callback.from_user.id)
        if balance < ADVICE_PRICE:
            # 👇 ТУТ ЗМІНЕНО: Правильна назва
            await send_stars_invoice(
                callback=callback,
                title="Порада Всесвіту 🧘",
                description="Коротка мудрість або відповідь на чітке запитання.",
                amount_stars=ADVICE_PRICE,
                payload=f"topup:{ADVICE_PRICE}"
            )
            return
        
        try:
            await increment_balance(db, callback.from_user.id, -ADVICE_PRICE)
        except InsufficientBalanceError:
            if callback.message:
                await callback.message.answer("Недостатньо ⭐ для оплати.")
            return

    await state.set_state(AdviceStates.waiting_for_question)
    # Зберігаємо ціну для повернення
    await state.update_data(price=ADVICE_PRICE)
    
    if callback.message:
        await callback.message.answer(
            "Напишіть своє запитання Всесвіту (або відправте '...', щоб отримати загальну пораду):",
            reply_markup=back_to_menu_kb()
        )

@router.message(AdviceStates.waiting_for_question)
async def advice_process(message: Message, state: FSMContext, advice_model: Any, db: firestore.Client) -> None:
    if not message.from_user: return
    user_text = message.text or "Загальна порада"
    
    # Дістаємо ціну для повернення
    data = await state.get_data()
    price = data.get("price", 1)

    msg = await message.answer("🧘 <i>З'єднуюсь з потоком...</i>", reply_markup=ReplyKeyboardRemove())
    
    prompt = f"Користувач запитує: '{user_text}'. Дай глибоку, філософську, але практичну пораду. Використовуй емодзі."
    text = await _gemini_text(advice_model, prompt)
    
    await msg.delete()

    # 👇 ЛОГІКА ПОВЕРНЕННЯ КОШТІВ
    if not text:
        is_admin = message.from_user.id in ADMIN_IDS
        refund_note = ""
        if not is_admin:
            try:
                await increment_balance(db, message.from_user.id, price)
                refund_note = f"Твої <b>{price} ⭐️ автоматично повернуто</b>."
            except: pass
        
        await message.answer(f"Вибач, Всесвіт зараз мовчить. {refund_note}", reply_markup=main_menu_kb())
        await state.clear()
        return

    # Відправка картинки та тексту
    await message.answer_photo(photo=IMG_ADVICE, caption="✨ <i>Відповідь Всесвіту:</i>")
    await message.answer(text, reply_markup=main_menu_kb())
    await state.clear()