from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime
from typing import Any

# 👇 СТАРИЙ ІМПОРТ
import google.generativeai as genai
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from firebase_admin import firestore

from firebase_db import InsufficientBalanceError, ensure_user, get_balance, increment_balance
from handlers.payment import send_stars_invoice
from keyboards import CB_CAREER, CB_DAILY, CB_RELATIONSHIP, back_to_menu_kb, main_menu_kb

router = Router()

RELATIONSHIP_PRICE = 1
CAREER_PRICE = 1
ADMIN_IDS = [469764985] 

FOOTER_TEXT = "\n\n💫 <i>Відчуваєш, що це не все? Карти готові відкрити більше. Обери тему нижче 👇</i>"

class ReadingStates(StatesGroup):
    waiting_for_context = State()

# 👇 СТАРА ФУНКЦІЯ (Text)
async def _gemini_generate_text(model: Any, prompt: str) -> str:
    def _call_sync() -> str:
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", None)
        return (text or "").strip()
    return await asyncio.to_thread(_call_sync)

# 👇 СТАРА ФУНКЦІЯ (Audio - через файл)
async def _gemini_generate_with_audio(model: Any, prompt: str, audio_bytes: bytes) -> str:
    def _call_sync() -> str:
        # Створюємо тимчасовий файл
        fd, path = tempfile.mkstemp(suffix=".ogg")
        os.close(fd)
        try:
            with open(path, "wb") as f:
                f.write(audio_bytes)
            
            # Завантажуємо файл в Gemini
            uploaded = genai.upload_file(path)
            
            # Генеруємо відповідь
            resp = model.generate_content([prompt, uploaded])
            text = getattr(resp, "text", None)
            return (text or "").strip()
        finally:
            # Прибираємо сміття
            try:
                os.remove(path)
            except OSError:
                pass
    return await asyncio.to_thread(_call_sync)

async def _send_long(message: Message, text: str) -> None:
    if not text:
        await message.answer("Сталося щось дивне — я не отримала відповідь. Спробуй ще раз.")
        return
    final_text = text + FOOTER_TEXT
    limit = 3900
    for i in range(0, len(final_text), limit):
        await message.answer(final_text[i : i + limit])

# --- HANDLERS ---

@router.callback_query(F.data == CB_DAILY)
async def daily_card(callback: CallbackQuery, db: firestore.Client, tarot_model: Any) -> None:
    if not callback.from_user: return
    user_id = str(callback.from_user.id)
    await ensure_user(db, user_id=callback.from_user.id, username=callback.from_user.username or "", first_name=callback.from_user.first_name or "")
    
    # ... (Логіка перевірки дати тут та сама, скорочено для зручності) ...
    is_admin = callback.from_user.id in ADMIN_IDS
    if not is_admin:
        today_str = datetime.now().strftime("%Y-%m-%d")
        doc = db.collection("users").document(user_id).get()
        user_data = doc.to_dict() or {}
        if user_data.get("last_daily_card_date") == today_str:
            await callback.answer("Твоя карта на сьогодні вже відкрита!", show_alert=True)
            return

    await callback.answer()
    msg = await callback.message.answer("🔮 <i>Запитую карту дня...</i>")
    
    prompt = "Витягни для мене карту дня і поясни енергію цього дня. Виділи афірмацію жирним курсивом і додай смайлик ✨."
    
    try:
        text = await _gemini_generate_text(tarot_model, prompt)
        
        db.collection("users").document(user_id).update({"last_daily_card_date": datetime.now().strftime("%Y-%m-%d")})
        await msg.delete()
        if callback.message:
            await _send_long(callback.message, text)
            await callback.message.answer("Обери наступну дію:", reply_markup=main_menu_kb())
    except Exception as e:
        print(f"Error: {e}")
        await msg.edit_text("Вибач, магічний ефір зараз перевантажений.")

# ... (Інші хендлери оплати залишаються як були, тільки виклик генерації змінюється) ...

@router.callback_query(F.data == CB_RELATIONSHIP)
async def relationship_reading(callback: CallbackQuery, state: FSMContext, db: firestore.Client) -> None:
    # Використовуємо стару функцію оплати
    from handlers.tarot import _start_paid_reading # (або визначте її тут)
    await _start_paid_reading(callback=callback, state=state, db=db, price=RELATIONSHIP_PRICE, reading_key="relationship")

@router.callback_query(F.data == CB_CAREER)
async def career_reading(callback: CallbackQuery, state: FSMContext, db: firestore.Client) -> None:
    from handlers.tarot import _start_paid_reading
    await _start_paid_reading(callback=callback, state=state, db=db, price=CAREER_PRICE, reading_key="career")

# Допоміжна функція оплати (поверніть її код, якщо вона була окремо)
async def _start_paid_reading(*, callback: CallbackQuery, state: FSMContext, db: firestore.Client, price: int, reading_key: str) -> None:
    # ... (Ваш код перевірки балансу) ...
    # Якщо баланс ок:
    await state.set_state(ReadingStates.waiting_for_context)
    await state.update_data(reading_key=reading_key)
    await callback.answer()
    if callback.message:
        await callback.message.answer("Опиши свою ситуацію...", reply_markup=back_to_menu_kb())

@router.message(ReadingStates.waiting_for_context)
async def reading_context_message(message: Message, state: FSMContext, db: firestore.Client, bot: Bot, tarot_model: Any) -> None:
    if not message.from_user: return
    msg = await message.answer("🔮 <i>Розкладаю карти...</i>")
    
    data = await state.get_data()
    reading_key = data.get("reading_key")
    topic = "стосунки" if reading_key == "relationship" else "кар'єра"

    if message.voice:
        buf = await bot.download(message.voice.file_id)
        audio_bytes = buf.getvalue()
        prompt = f"Контекст про {topic} (голос). Зроби розклад."
        text = await _gemini_generate_with_audio(tarot_model, prompt, audio_bytes)
    else:
        user_text = message.text or ""
        prompt = f"Контекст про {topic}: {user_text}. Зроби розклад."
        text = await _gemini_generate_text(tarot_model, prompt)

    await msg.delete()
    await _send_long(message, text)
    await state.clear()