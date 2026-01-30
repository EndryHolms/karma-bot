from __future__ import annotations

import asyncio
from typing import Any

from aiogram import F, Router
from aiogram.types import CallbackQuery
from firebase_admin import firestore

from firebase_db import InsufficientBalanceError, ensure_user, get_balance, increment_balance
from handlers.payment import send_stars_invoice
from keyboards import CB_ADVICE, back_to_menu_kb

router = Router()

ADVICE_PRICE = 25


async def _gemini_generate_text(model: Any, prompt: str) -> str:
    def _call_sync() -> str:
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", None)
        return (text or "").strip()

    return await asyncio.to_thread(_call_sync)


@router.callback_query(F.data == CB_ADVICE)
async def universe_advice(callback: CallbackQuery, db: firestore.Client, advice_model: Any) -> None:
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
    if balance < ADVICE_PRICE:
        await callback.answer("Недостатньо ⭐ — відкриваю оплату…")
        await send_stars_invoice(
            callback=callback,
            title="Поповнення балансу Karma",
            description=f"Поповнення на {ADVICE_PRICE} ⭐ для Universe Advice.",
            amount_stars=ADVICE_PRICE,
            payload=f"topup:{ADVICE_PRICE}",
        )
        return

    try:
        await increment_balance(db, callback.from_user.id, -ADVICE_PRICE)
    except InsufficientBalanceError:
        await callback.answer("Недостатньо ⭐ — відкриваю оплату…")
        await send_stars_invoice(
            callback=callback,
            title="Поповнення балансу Karma",
            description=f"Поповнення на {ADVICE_PRICE} ⭐ для Universe Advice.",
            amount_stars=ADVICE_PRICE,
            payload=f"topup:{ADVICE_PRICE}",
        )
        return

    await callback.answer("Слухаю Всесвіт…")

    prompt = "Дай мені пораду Всесвіту на сьогодні."
    text = await _gemini_generate_text(advice_model, prompt)

    if callback.message:
        await callback.message.answer(text)
        await callback.message.answer("Обери наступну дію:", reply_markup=back_to_menu_kb())
