from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime
from typing import Any

# 👇 Використовуємо аліас
import google.generativeai as genai

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from firebase_admin import firestore

from firebase_db import InsufficientBalanceError, ensure_user, get_balance, increment_balance
from handlers.payment import send_stars_invoice
from keyboards import CB_CAREER, CB_DAILY, CB_RELATIONSHIP, back_to_menu_kb, main_menu_kb

router = Router()

# 👇 Налаштування цін
RELATIONSHIP_PRICE = 1
CAREER_PRICE = 1
# Краще винести це в .env, але поки нехай буде тут
ADMIN_IDS = [469764985]

FOOTER_TEXT = "\n\n💫 <i>Відчуваєш, що це не все? Карти готові відкрити більше. Обери тему нижче 👇</i>"

class ReadingStates(StatesGroup):
    waiting_for_context = State()

# --- ФУНКЦІЇ ГЕНЕРАЦІЇ (без змін) ---
async def _gemini_generate_text(model: Any, prompt: str) -> str:
    def _call_sync() -> str:
        try:
            resp = model.generate_content(prompt)
            text = getattr(resp, "text", None)
            return (text or "").strip()
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
            text = getattr(resp, "text", None)
            return (text or "").strip()
        except Exception as e:
            print(f"GenAI Audio Error: {e}")
            return ""
        finally:
            try: os.remove(path)
            except OSError: pass
    return await asyncio.to_thread(_call_sync)

async def _send_long(message: Message, text: str, reply_markup: Any = None) -> None:
    if not text:
        await message.answer("Сталося щось дивне — я не отримала відповідь. Спробуй ще раз.", reply_markup=reply_markup)
        return
    final_text = text + FOOTER_TEXT
    limit = 4000
    chunks = [final_text[i : i + limit] for i in range(0, len(final_text), limit)]
    for i, chunk in enumerate(chunks):
        is_last = (i == len(chunks) - 1)
        if is_last:
            await message.answer(chunk, reply_markup=reply_markup)
        else:
            await message.answer(chunk)

# --- HANDLERS ---

@router.callback_query(F.data == CB_DAILY)
async def daily_card(callback: CallbackQuery, db: firestore.Client, tarot_model: Any) -> None:
    if not callback.from_user: return
    user_id = str(callback.from_user.id)
    await ensure_user(db, user_id=callback.from_user.id, username=callback.from_user.username or "", first_name=callback.from_user.first_name or "")
    
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
    await asyncio.sleep(2.0)
    await msg.edit_text("🧘 <i>Налаштовуюся на твої вібрації...</i>")
    await asyncio.sleep(2.0)
    await msg.edit_text("🎴 <i>Тасую колоду...</i>")
    
    prompt = "Витягни для мене карту дня і поясни енергію цього дня. Виділи афірмацію жирним курсивом і додай смайлик ✨."
    
    try:
        text = await _gemini_generate_text(tarot_model, prompt)
        if text:
            db.collection("users").document(user_id).update({"last_daily_card_date": datetime.now().strftime("%Y-%m-%d")})
        await msg.delete()
        if callback.message:
            await _send_long(callback.message, text, reply_markup=main_menu_kb())
    except Exception as e:
        print(f"Daily Handler Error: {e}")
        await msg.edit_text("Вибач, магічний ефір зараз перевантажений.", reply_markup=main_menu_kb())


@router.callback_query(F.data == CB_RELATIONSHIP)
async def relationship_reading(callback: CallbackQuery, state: FSMContext, db: firestore.Client) -> None:
    # 👇 Передаємо конкретну назву і опис
    await _start_paid_reading(
        callback=callback, state=state, db=db, 
        price=RELATIONSHIP_PRICE, 
        reading_key="relationship",
        title="Розклад: Любов ❤️",
        description="Аналіз стосунків, почуттів та перспектив."
    )


@router.callback_query(F.data == CB_CAREER)
async def career_reading(callback: CallbackQuery, state: FSMContext, db: firestore.Client) -> None:
    # 👇 Передаємо конкретну назву і опис
    await _start_paid_reading(
        callback=callback, state=state, db=db, 
        price=CAREER_PRICE, 
        reading_key="career",
        title="Розклад: Кар'єра 💰",
        description="Аналіз фінансів, роботи та проектів."
    )


async def _start_paid_reading(*, callback: CallbackQuery, state: FSMContext, db: firestore.Client, price: int, reading_key: str, title: str, description: str) -> None:
    """Перевірка оплати і початок діалогу з динамічним чеком."""
    if not callback.from_user: return
    await ensure_user(db, user_id=callback.from_user.id, username=callback.from_user.username or "", first_name=callback.from_user.first_name or "")

    await callback.answer()

    is_admin = callback.from_user.id in ADMIN_IDS
    if is_admin:
        if callback.message:
            await callback.message.answer("👑 Admin Mode: Оплата пропущена.")
    else:
        balance = await get_balance(db, callback.from_user.id)
        if balance < price:
            # 👇 Використовуємо передані title та description
            await send_stars_invoice(
                callback=callback,
                title=title,
                description=description,
                amount_stars=price,
                payload=f"topup:{price}", # Це поповнення балансу під конкретну послугу
            )
            return
        
        try:
            await increment_balance(db, callback.from_user.id, -price)
        except InsufficientBalanceError:
            if callback.message:
                await callback.message.answer("Недостатньо ⭐ для оплати.")
            return

    await state.set_state(ReadingStates.waiting_for_context)
    await state.update_data(reading_key=reading_key)
    
    if callback.message:
        if reading_key == "relationship":
            await callback.message.answer(
                "Зосередься на людині. Напиши її ім'я та коротко опиши, що відбувається між вами зараз.",
                reply_markup=back_to_menu_kb()
            )
        elif reading_key == "career":
            await callback.message.answer(
                "Опиши свою робочу ситуацію або проект, який тебе турбує.",
                reply_markup=back_to_menu_kb()
            )
        else:
            await callback.message.answer(
                "Опиши свою ситуацію (текстом або голосом)...",
                reply_markup=back_to_menu_kb()
            )

# --- БЛОК reading_context_message залишається без змін ---
@router.message(ReadingStates.waiting_for_context)
async def reading_context_message(message: Message, state: FSMContext, db: firestore.Client, bot: Any, tarot_model: Any) -> None:
    # ... (код той самий, що і був) ...
    if not message.from_user: return
    
    data = await state.get_data()
    reading_key = data.get("reading_key")
    topic = "стосунки" if reading_key == "relationship" else "кар'єра"

    wait_text = "🔮 <i>Розкладаю карти...</i>"
    if reading_key == "relationship":
        wait_text = "<i>Karma розкладає карти на: Ваші почуття, Приховані думки, Майбутнє...</i>"

    msg = await message.answer(wait_text, reply_markup=ReplyKeyboardRemove())
    
    text = ""
    try:
        if message.voice:
            file_info = await bot.get_file(message.voice.file_id)
            file_path = file_info.file_path
            downloaded_file = await bot.download_file(file_path)
            audio_bytes = downloaded_file.read()

            prompt = f"Контекст про {topic} (голос). Зроби розклад."
            text = await _gemini_generate_with_audio(tarot_model, prompt, audio_bytes)
        else:
            user_text = message.text or ""
            prompt = f"Контекст про {topic}: {user_text}. Зроби розклад."
            text = await _gemini_generate_text(tarot_model, prompt)
            
    except Exception as e:
        print(f"Reading Context Error: {e}")
        text = ""

    await msg.delete()
    await _send_long(message, text, reply_markup=main_menu_kb())
    await state.clear()