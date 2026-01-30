from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from firebase_admin import firestore

from firebase_db import ensure_user, get_balance
from keyboards import CB_BACK_MENU, CB_PROFILE, main_menu_kb

router = Router()

WELCOME_IMAGE_URL = "https://i.postimg.cc/7hWHVtr6/Gemini-Generated-Image-y1ell9y1ell9y1el-(1).png"


@router.message(CommandStart())
async def cmd_start(message: Message, db: firestore.Client) -> None:
    user = message.from_user
    await ensure_user(
        db,
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
    )

    text = (
        f"Вітаю, <b>{user.first_name}</b>. Я — Karma.\n\n"
        "Я тут, щоб освітити твій шлях, коли стає темно. "
        "Пам'ятай: карти не вирішують за тебе, вони лише показують вірогідності.\n\n"
        "<b>Що турбує твою душу сьогодні?</b>"
    )

    try:
        await message.answer_photo(
            photo=WELCOME_IMAGE_URL,
            caption=text,
            reply_markup=main_menu_kb(),
        )
    except Exception:
        await message.answer(text, reply_markup=main_menu_kb())


@router.callback_query(F.data == CB_BACK_MENU)
async def back_to_menu(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.delete()
        await callback.message.answer("Головне меню:", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == CB_PROFILE)
async def profile(callback: CallbackQuery, db: firestore.Client) -> None:
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

    # 👇 ОНОВЛЕНИЙ МАГІЧНИЙ ТЕКСТ 👇
    text = (
        f"<b>🧘 Твій енергетичний баланс:</b>\n"
        f"✨ Доступно зірок: <b>{balance} ⭐️</b>\n\n"
        "<b>Як поповнити запаси?</b>\n"
        "У Всесвіті діє закон обміну. Просто обери будь-який платний розклад, "
        "і якщо енергії не вистачить — я підкажу шлях до відновлення балансу.\n\n"
        "<i>Енергія нікуди не зникає, вона лише змінює форму.</i>"
    )

    if callback.message:
        # Використовуємо edit_text, щоб не плодити повідомлення
        await callback.message.edit_text(text, reply_markup=main_menu_kb())

    await callback.answer()