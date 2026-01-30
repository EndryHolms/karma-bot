from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime
from typing import Any

import google.generativeai as genai
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from firebase_admin import firestore

from firebase_db import InsufficientBalanceError, ensure_user, get_balance, increment_balance
from handlers.payment import send_stars_invoice
# 👇 ДОДАНО main_menu_kb в імпорти
from keyboards import (
    CB_CAREER,
    CB_DAILY,
    CB_RELATIONSHIP,
    back_to_menu_kb,
    main_menu_kb, 
)

router = Router()

RELATIONSHIP_PRICE = 75
CAREER_PRICE = 100

# Вставте сюди свій ID, якщо він зник під час копіювання
ADMIN_IDS = [469764985] 

FOOTER_TEXT = (
    "\n\n✨ <i>Відчуваєш, що це не все? Карти готові відкрити більше. "
    "Обери тему нижче 👇</i>"
)


class ReadingStates(StatesGroup):
    waiting_for_context = State()


async def _gemini_generate_text(model: Any, prompt: str) -> str:
    def _call_sync() -> str:
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", None)
        return (text or "").strip()

    return await asyncio.to_thread(_call_sync)


async def _gemini_generate_with_audio(model: Any, prompt: str, audio_bytes: bytes, mime_type: str) -> str:
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
        finally:
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


@router.callback_query(F.data == CB_DAILY)
async def daily_card(callback: CallbackQuery, db: firestore.Client, tarot_model: Any) -> None:
    if not callback.from_user:
        await callback.answer()
        return

    user_id = str(callback.from_user.id)

    await ensure_user(
        db,
        user_id=callback.from_user.id,
        username=callback.from_user.username or "",
        first_name=callback.from_user.first_name or "",
    )

    is_admin = callback.from_user.id in ADMIN_IDS

    if not is_admin:
        today_str = datetime.now().strftime("%Y-%m-%d")
        doc_ref = db.collection("users").document(user_id)
        doc = doc_ref.get()
        user_data = doc.to_dict() or {}
        last_run = user_data.get("last_daily_card_date")

        if last_run == today_str:
            await callback.answer("Сьогодні ти вже отримав карту!", show_alert=True)
            if callback.message:
                 await callback.message.answer(
                    "🔮 <b>Сьогодні зірки вже промовили до тебе.</b>\n\n"
                    "Не спокушай долю частими питаннями. Обдумай отриману відповідь.\n"
                    "Приходь завтра за новою порадою. ✨"
                )
            return
    else:
        today_str = datetime.now().strftime("%Y-%m-%d")
        doc_ref = db.collection("users").document(user_id)


    await callback.answer()
    
    msg = await callback.message.answer("🔮 <i>Запитую карту дня...</i>")
    await asyncio.sleep(1.5)
    await msg.edit_text("✨ <i>Налаштовуюся на твої вібрації...</i>")
    await asyncio.sleep(1.5)
    await msg.edit_text("🎴 <i>Тасую колоду...</i>")
    
    prompt = "Витягни для мене карту дня і поясни енергію цього дня."
    
    try:
        text = await _gemini_generate_text(tarot_model, prompt)
        
        doc_ref.update({"last_daily_card_date": today_str})

        await msg.delete()

        if callback.message:
            await _send_long(callback.message, text)
            # 👇 ТУТ ЗМІНЕНО: показуємо повне меню замість "Назад"
            await callback.message.answer("Обери наступну дію:", reply_markup=main_menu_kb())
            
    except Exception as e:
        print(f"Error: {e}")
        await msg.edit_text("Вибач, магічний ефір зараз перевантажений. Спробуй пізніше.")


async def _start_paid_reading(
    *,
    callback: CallbackQuery,
    state: FSMContext,
    db: firestore.Client,
    price: int,
    reading_key: str,
) -> None:
    if not callback.from_user:
        await callback.answer()
        return

    await ensure_user(
        db,
        user_id=callback.from_user.id,
        username=callback.from_user.username or "",
        first_name=callback.from_user.first_name or "",
    )

    if callback.from_user.id in ADMIN_IDS:
        await callback.answer("👑 Режим Адміна: Доступ відкрито!")
        await state.set_state(ReadingStates.waiting_for_context)
        await state.update_data(reading_key=reading_key)
        
        if callback.message:
            await callback.message.answer(
                "👑 <b>Admin Mode:</b> Оплата пропущена.\n"
                "Опиши ситуацію (текст/голос):",
                reply_markup=back_to_menu_kb(),
            )
        return

    balance = await get_balance(db, callback.from_user.id)
    if balance < price:
        await callback.answer("Недостатньо ⭐ — відкриваю оплату…")
        await send_stars_invoice(
            callback=callback,
            title="Поповнення балансу Karma",
            description=f"Поповнення на {price} ⭐ для доступу до читання.",
            amount_stars=price,
            payload=f"topup:{price}",
        )
        return

    try:
        await increment_balance(db, callback.from_user.id, -price)
    except InsufficientBalanceError:
        await callback.answer("Недостатньо ⭐ — відкриваю оплату…")
        await send_stars_invoice(
            callback=callback,
            title="Поповнення балансу Karma",
            description=f"Поповнення на {price} ⭐ для доступу до читання.",
            amount_stars=price,
            payload=f"topup:{price}",
        )
        return

    await state.set_state(ReadingStates.waiting_for_context)
    await state.update_data(reading_key=reading_key)

    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "Опиши свою ситуацію (можна текстом або голосом). "
            "Я подивлюсь глибше…",
            reply_markup=back_to_menu_kb(),
        )


@router.callback_query(F.data == CB_RELATIONSHIP)
async def relationship_reading(
    callback: CallbackQuery,
    state: FSMContext,
    db: firestore.Client,
) -> None:
    await _start_paid_reading(
        callback=callback,
        state=state,
        db=db,
        price=RELATIONSHIP_PRICE,
        reading_key="relationship",
    )


@router.callback_query(F.data == CB_CAREER)
async def career_reading(
    callback: CallbackQuery,
    state: FSMContext,
    db: firestore.Client,
) -> None:
    await _start_paid_reading(
        callback=callback,
        state=state,
        db=db,
        price=CAREER_PRICE,
        reading_key="career",
    )


@router.message(ReadingStates.waiting_for_context)
async def reading_context_message(
    message: Message,
    state: FSMContext,
    db: firestore.Client,
    bot: Bot,
    tarot_model: Any,
) -> None:
    if not message.from_user:
        return

    msg = await message.answer("✨ <i>Зчитую твій запит...</i>")
    await asyncio.sleep(1.5)
    await msg.edit_text("🔮 <i>Розкладаю карти...</i>")

    data = await state.get_data()
    reading_key = data.get("reading_key")

    await ensure_user(
        db,
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
    )

    if reading_key == "relationship":
        topic = "стосунки"
        extra = "Зосередься на почуттях, мотивах, прихованих страхах і чесному напрямку."
    else:
        topic = "кар'єра/гроші"
        extra = "Зосередься на можливостях, ризиках, ресурсах і практичних кроках."

    if message.voice:
        buf = await bot.download(message.voice.file_id)
        audio_bytes = buf.getvalue()
        prompt = (
            f"Користувач надіслав голосове повідомлення з контекстом про {topic}. "
            f"Спочатку зрозумій/транскрибуй зміст українською, потім зроби розклад. {extra}"
        )
        text = await _gemini_generate_with_audio(tarot_model, prompt, audio_bytes, "audio/ogg")
    else:
        user_text = (message.text or "").strip()
        if not user_text:
            await msg.delete()
            await message.answer("Надішли, будь ласка, текстом або голосом — я не бачу контексту.")
            return

        prompt = (
            f"Контекст користувача про {topic}:\n{user_text}\n\n"
            f"Зроби глибоке таро-читання. {extra}"
        )
        text = await _gemini_generate_text(tarot_model, prompt)

    await msg.delete()

    await _send_long(message, text)
    # 👇 ТУТ ТЕЖ ЗМІНЕНО: показуємо повне меню замість "Назад"
    await message.answer("Обери наступну дію:", reply_markup=main_menu_kb())
    await state.clear()