from __future__ import annotations

import asyncio
from typing import Any

from aiogram import F, Router
from aiogram.types import CallbackQuery
from firebase_admin import firestore

from firebase_db import InsufficientBalanceError, ensure_user, get_balance, increment_balance
from handlers.payment import send_stars_invoice
from keyboards import CB_ADVICE, main_menu_kb
# 👇 Імпортуємо системний промпт
from prompts import UNIVERSE_ADVICE_SYSTEM_PROMPT

router = Router()

# 👇 Тестова ціна (1 зірка)
ADVICE_PRICE = 1

ADMIN_IDS = [469764985] 

# 👇 Нова модель
MODEL_NAME = "gemini-2.0-flash"


# 👇 ОНОВЛЕНА ФУНКЦІЯ (працює з genai_client)
async def _gemini_generate_text(client: Any, prompt: str) -> str:
    def _call_sync() -> str:
        # Виклик через новий SDK
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config={"system_instruction": UNIVERSE_ADVICE_SYSTEM_PROMPT}
        )
        return response.text if response.text else ""
    return await asyncio.to_thread(_call_sync)


@router.callback_query(F.data == CB_ADVICE)
async def get_advice(
    callback: CallbackQuery, 
    db: firestore.Client, 
    # 👇 Тут тепер genai_client замість advice_model
    genai_client: Any 
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

    is_admin = callback.from_user.id in ADMIN_IDS

    if is_admin:
        await callback.answer("👑 Режим Адміна: Безкоштовно!")
    else:
        balance = await get_balance(db, callback.from_user.id)
        if balance < ADVICE_PRICE:
            await callback.answer("Недостатньо ⭐ — відкриваю оплату…")
            await send_stars_invoice(
                callback=callback,
                title="Порада Всесвіту",
                description="Отримати мудру пораду від карт Таро.",
                amount_stars=ADVICE_PRICE,
                payload=f"topup:{ADVICE_PRICE}",
            )
            return

        try:
            await increment_balance(db, callback.from_user.id, -ADVICE_PRICE)
        except InsufficientBalanceError:
            await callback.answer("Недостатньо ⭐")
            return

    await callback.answer()
    msg = await callback.message.answer("🧘 <i>З'єднуюсь з потоком...</i>")
    await asyncio.sleep(1.5)
    await msg.edit_text("✨ <i>Слухаю шепіт Всесвіту...</i>")
    
    # Текст запиту (системна інструкція додається автоматично в _gemini_generate_text)
    prompt = (
        "Дай коротку, глибоку і філософську пораду від імені Всесвіту/Таро для цієї людини на сьогодні. "
        "Порада має бути підтримуючою і мудрою. "
        "Закінчи повідомлення короткою афірмацією. Виділи афірмацію жирним курсивом."
    )
    
    try:
        # Передаємо genai_client
        text = await _gemini_generate_text(genai_client, prompt)
        
        await msg.delete()
        
        if callback.message:
            await callback.message.answer(text)
            await callback.message.answer("Обери наступну дію:", reply_markup=main_menu_kb())
            
    except Exception as e:
        print(f"Error: {e}")
        await msg.edit_text("Ефір зараз закритий хмарами. Спробуй пізніше.")