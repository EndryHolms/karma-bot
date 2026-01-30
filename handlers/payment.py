from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from firebase_admin import firestore

from firebase_db import ensure_user, increment_balance

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
async def successful_payment(message: Message, db: firestore.Client) -> None:
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

    await message.answer(
        f"<b>Баланс поповнено!</b> Додано <b>{total_amount} ⭐</b>.\n"
        "Спробуй запит ще раз з меню."  # user can re-run the paid feature
    )
