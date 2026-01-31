from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime
from typing import Any

# 👇 Використовуємо стару бібліотеку
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

# 👇 Налаштування
RELATIONSHIP_PRICE = 1
CAREER_PRICE = 1
ADMIN_IDS = [469764985]  # Ваш ID

FOOTER_TEXT = "\n\n💫 <i>Відчуваєш, що це не все? Карти готові відкрити більше. Обери тему нижче 👇</i>"

class ReadingStates(StatesGroup):
    waiting_for_context = State()

# --- ФУНКЦІЇ ГЕНЕРАЦІЇ (WRAPPER) ---

async def _gemini_generate_text(model: Any, prompt: str) -> str:
    """Генерує текст (синхронний виклик в окремому потоці)."""
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
    """Генерує текст на основі аудіо (через тимчасовий файл)."""
    def _call_sync() -> str:
        # Створюємо тимчасовий файл, бо стара бібліотека хоче шлях до файлу
        fd, path = tempfile.mkstemp(suffix=".ogg")
        os.close(fd)
        try:
            with open(path, "wb") as f:
                f.write(audio_bytes)
            
            # Завантажуємо файл
            uploaded = genai.upload_file(path)
            
            # Генеруємо відповідь
            resp = model.generate_content([prompt, uploaded])
            text = getattr(resp, "text", None)
            return (text or "").strip()
        except Exception as e:
            print(f"GenAI Audio Error: {e}")
            return ""
        finally:
            # Прибираємо за собою
            try:
                os.remove(path)
            except OSError:
                pass
    return await asyncio.to_thread(_call_sync)

async def _send_long(message: Message, text: str, reply_markup: Any = None) -> None:
    """Розбиває довгий текст на частини і додає кнопки до останньої."""
    if not text:
        await message.answer("Сталося щось дивне — я не отримала відповідь. Спробуй ще раз.", reply_markup=reply_markup)
        return

    final_text = text + FOOTER_TEXT
    limit = 4000 # Ліміт Telegram
    
    chunks = [final_text[i : i + limit] for i in range(0, len(final_text), limit)]
    
    for i, chunk in enumerate(chunks):
        is_last = (i == len(chunks) - 1)
        
        if is_last:
            # До останнього шматка чіпляємо кнопки
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
    
    prompt = "Витягни для мене карту дня і поясни енергію цього дня. Виділи афірмацію жирним курсивом і додай смайлик ✨."
    
    try:
        text = await _gemini_generate_text(tarot_model, prompt)
        
        if text:
            # Оновлюємо дату, тільки якщо отримали відповідь
            db.collection("users").document(user_id).update({"last_daily_card_date": datetime.now().strftime("%Y-%m-%d")})
        
        await msg.delete()
        if callback.message:
            await _send_long(callback.message, text, reply_markup=main_menu_kb())
            
    except Exception as e:
        print(f"Daily Handler Error: {e}")
        await msg.edit_text("Вибач, магічний ефір зараз перевантажений.", reply_markup=main_menu_kb())


@router.callback_query(F.data == CB_RELATIONSHIP)
async def relationship_reading(callback: CallbackQuery, state: FSMContext, db: firestore.Client) -> None:
    await _start_paid_reading(callback=callback, state=state, db=db, price=RELATIONSHIP_PRICE, reading_key="relationship")


@router.callback_query(F.data == CB_CAREER)
async def career_reading(callback: CallbackQuery, state: FSMContext, db: firestore.Client) -> None:
    await _start_paid_reading(callback=callback, state=state, db=db, price=CAREER_PRICE, reading_key="career")


async def _start_paid_reading(*, callback: CallbackQuery, state: FSMContext, db: firestore.Client, price: int, reading_key: str) -> None:
    """Універсальна функція для платних розкладів."""
    if not callback.from_user: return
    await ensure_user(db, user_id=callback.from_user.id, username=callback.from_user.username or "", first_name=callback.from_user.first_name or "")

    # Спочатку відповідаємо на колбек, щоб прибрати "годинничок"
    await callback.answer()

    is_admin = callback.from_user.id in ADMIN_IDS
    if is_admin:
        # 👇 Видиме повідомлення для адміна
        if callback.message:
            await callback.message.answer("👑 Admin Mode: Оплата пропущена (безкоштовно).")
    else:
        balance = await get_balance(db, callback.from_user.id)
        if balance < price:
            await send_stars_invoice(
                callback=callback,
                title="Розклад Таро",
                description="Індивідуальний розклад карт.",
                amount_stars=price,
                payload=f"topup:{price}",
            )
            return
        
        try:
            await increment_balance(db, callback.from_user.id, -price)
        except InsufficientBalanceError:
            if callback.message:
                await callback.message.answer("Недостатньо ⭐ для оплати.")
            return

    # Якщо все ок (адмін або оплатив), переходимо до стану
    await state.set_state(ReadingStates.waiting_for_context)
    await state.update_data(reading_key=reading_key)
    
    if callback.message:
        await callback.message.answer("Опиши свою ситуацію (текстом або голосом)...", reply_markup=back_to_menu_kb())


@router.message(ReadingStates.waiting_for_context)
async def reading_context_message(message: Message, state: FSMContext, db: firestore.Client, bot: Any, tarot_model: Any) -> None:
    if not message.from_user: return
    
    # Прибираємо кнопку "Назад"
    msg = await message.answer("🔮 <i>Розкладаю карти...</i>", reply_markup=ReplyKeyboardRemove())
    
    data = await state.get_data()
    reading_key = data.get("reading_key")
    topic = "стосунки" if reading_key == "relationship" else "кар'єра"

    text = ""
    try:
        if message.voice:
            # Завантаження голосу
            file_info = await bot.get_file(message.voice.file_id)
            file_path = file_info.file_path
            
            # Скачуємо файл у пам'ять
            downloaded_file = await bot.download_file(file_path)
            audio_bytes = downloaded_file.read()

            prompt = f"Контекст про {topic} (голос). Зроби розклад."
            text = await _gemini_generate_with_audio(tarot_model, prompt, audio_bytes)
        else:
            # Текстовий запит
            user_text = message.text or ""
            prompt = f"Контекст про {topic}: {user_text}. Зроби розклад."
            text = await _gemini_generate_text(tarot_model, prompt)
            
    except Exception as e:
        print(f"Reading Context Error: {e}")
        text = ""

    await msg.delete()
    
    # Відправляємо результат з кнопками в кінці
    await _send_long(message, text, reply_markup=main_menu_kb())
    
    # Очищаємо стан
    await state.clear()