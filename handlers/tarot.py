from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Any

import google.generativeai as genai
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from firebase_admin import firestore

from firebase_db import InsufficientBalanceError, ensure_user, get_balance, increment_balance
from handlers.payment import send_stars_invoice
from keyboards import (
    CB_CAREER,
    CB_DAILY,
    CB_RELATIONSHIP,
    back_to_menu_kb,
)

router = Router()

RELATIONSHIP_PRICE = 75
CAREER_PRICE = 100


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

    limit = 3900
    for i in range(0, len(text), limit):
        await message.answer(text[i : i + limit])


@router.callback_query(F.data == CB_DAILY)
async def daily_card(callback: CallbackQuery, db: firestore.Client, tarot_model: Any) -> None:
    if not callback.from_user:
        await callback.answer()
        return

    await ensure_user(
        db,
        user_id=callback.from_user.id,
        username=callback.from_user.username or "",
        first_name=callback.from_user.first_name or "",
    )

    await callback.answer("Читаю енергію дня…")

    prompt = "Витягни для мене карту дня і поясни енергію цього дня."
    text = await _gemini_generate_text(tarot_model, prompt)

    if callback.message:
        await _send_long(callback.message, text)
        await callback.message.answer("Обери наступну дію:", reply_markup=back_to_menu_kb())


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
            await message.answer("Надішли, будь ласка, текстом або голосом — я не бачу контексту.")
            return

        prompt = (
            f"Контекст користувача про {topic}:\n{user_text}\n\n"
            f"Зроби глибоке таро-читання. {extra}"
        )
        text = await _gemini_generate_text(tarot_model, prompt)

    await _send_long(message, text)
    await message.answer("Обери наступну дію:", reply_markup=back_to_menu_kb())
    await state.clear()
