from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from firebase_admin import firestore

from firebase_db import ensure_user, increment_balance, get_user_language, claim_ai_action_lock
from lexicon import get_text
from keyboards import back_to_menu_kb
from handlers.tarot import ReadingStates
from handlers.advice import AdviceStates

router = Router()

PROVIDER_TOKEN = ""  # Telegram Stars do not require a provider token
CURRENCY_XTR = "XTR"


def build_prices(amount_stars: int) -> list[LabeledPrice]:
    return [LabeledPrice(label="Telegram Stars", amount=amount_stars)]


async def send_stars_invoice(
    *,
    callback: CallbackQuery,
    title: str,
    description: str,
    amount_stars: int,
    payload: str,
) -> None:
    if not callback.message:
        return

    await callback.message.answer_invoice(
        title=title,
        description=description,
        payload=payload,
        provider_token=PROVIDER_TOKEN,
        currency=CURRENCY_XTR,
        prices=build_prices(amount_stars),
    )


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, state: FSMContext, db: firestore.Client) -> None:
    sp = message.successful_payment
    if not sp or not message.from_user:
        return

    await ensure_user(
        db,
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
    )

    total_amount = int(sp.total_amount or 0)
    if total_amount > 0:
        await increment_balance(db, message.from_user.id, total_amount)

    lang = await get_user_language(db, message.from_user.id)
    payload = sp.invoice_payload or ""

    if payload.startswith("reading:"):
        parts = payload.split(":")
        reading_key = parts[1]
        price = int(parts[2])
        action_key = f"reading:{reading_key}"
        
        # Миттєво списуємо суму
        await increment_balance(db, message.from_user.id, -price)
        await claim_ai_action_lock(db, message.from_user.id, action_key)
        
        await state.set_state(ReadingStates.waiting_for_context)
        await state.update_data(reading_key=reading_key, price=price, action_key=action_key)
        
        prompt_key = "ask_love_context" if reading_key == "relationship" else "ask_career_context"
        
        await message.answer(
            f"<b>Баланс поповнено!</b>\n\n{get_text(lang, prompt_key)}",
            reply_markup=back_to_menu_kb(lang),
            parse_mode="HTML"
        )
        return

    elif payload.startswith("advice:"):
        price = int(payload.split(":")[1])
        action_key = "advice"
        
        # Миттєво списуємо суму
        await increment_balance(db, message.from_user.id, -price)
        await claim_ai_action_lock(db, message.from_user.id, action_key)
        
        await state.set_state(AdviceStates.waiting_for_question)
        await state.update_data(price=price, action_key=action_key)
        
        await message.answer(
            f"<b>Баланс поповнено!</b>\n\n{get_text(lang, 'ask_question')}",
            reply_markup=back_to_menu_kb(lang),
            parse_mode="HTML"
        )
        return

    # Fallback / старий topup (якщо хтось платить за старим інвойсом, який ще висить у чаті)
    await message.answer(
        f"<b>Баланс поповнено!</b> Додано <b>{total_amount} ⭐</b>.\n"
        "Спробуй запит ще раз з меню.",
        parse_mode="HTML"
    )
