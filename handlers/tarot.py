from __future__ import annotations
import asyncio
import os
from typing import Any

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from firebase_admin import firestore

from firebase_db import (
    InsufficientBalanceError,
    ensure_user,
    get_balance,
    get_user_language,
    increment_balance,
)
from keyboards import (
    CB_CAREER,
    CB_DAILY,
    CB_RELATIONSHIP,
    back_to_menu_kb,
    main_menu_kb,
)
from lexicon import get_text

from handlers.payment import send_stars_invoice

router = Router()

_admin_env = os.getenv("ADMIN_IDS", "469764985")
ADMIN_IDS = [int(x.strip()) for x in _admin_env.split(",") if x.strip().isdigit()]


class TarotForm(StatesGroup):
    question = State()


PRICES = {CB_RELATIONSHIP: 3, CB_CAREER: 3}

# Мультимовні картинки для розкладів
IMAGES_TAROT = {
    "uk": {
        CB_DAILY: "https://i.postimg.cc/kG6N0s03/image.png",
        CB_RELATIONSHIP: "https://i.postimg.cc/8PJHMgM9/b-A-richly-detailed-Ta-2.png",
        CB_CAREER: "https://i.postimg.cc/j2yN5sxm/b-A-richly-detailed-Ta-3.png",
    },
    "en": {
        CB_DAILY: "https://i.postimg.cc/FzXfSgpM/image.png",
        CB_RELATIONSHIP: "https://i.postimg.cc/Pq0wWJRL/b-A-richly-detailed-Ta-2-en.png",
        CB_CAREER: "https://i.postimg.cc/1zW1LzNn/b-A-richly-detailed-Ta-3-en.png",
    },
    "ru": {
        CB_DAILY: "https://i.postimg.cc/kG6N0s03/image.png", # Залишимо українську
        CB_RELATIONSHIP: "https://i.postimg.cc/y8p06v5v/b-A-richly-detailed-Ta-2-ru.png",
        CB_CAREER: "https://i.postimg.cc/wMP51G1C/b-A-richly-detailed-Ta-3-ru.png",
    },
}

async def _gemini_text(model: Any, prompt: str, system_instruction: str) -> str:
    """Обгортка для генерації тексту з динамічною системною інструкцією."""

    def _sync():
        try:
            resp = model.generate_content(prompt, system_instruction=system_instruction)
            return (getattr(resp, "text", "") or "").strip()
        except Exception as e:
            print(f"Tarot Gen Error: {e}")
            return ""

    return await asyncio.to_thread(_sync)


@router.callback_query(
    F.data.in_([CB_RELATIONSHIP, CB_CAREER, CB_DAILY])
)
async def tarot_reading_start(
    callback: CallbackQuery, state: FSMContext, db: firestore.Client
) -> None:
    if not callback.from_user:
        return

    await ensure_user(
        db,
        user_id=callback.from_user.id,
        username=callback.from_user.username or "",
        first_name=callback.from_user.first_name or "",
    )
    await callback.answer()

    lang = await get_user_language(db, callback.from_user.id)

    price = PRICES.get(callback.data, 0)
    is_admin = callback.from_user.id in ADMIN_IDS

    # Карта дня безкоштовна
    if callback.data == CB_DAILY:
        await state.update_data(reading_type=callback.data, price=0)
        # Переходимо одразу до обробки, минаючи запитання
        await tarot_reading_process(callback, state, db)
        return

    if not is_admin:
        balance = await get_balance(db, callback.from_user.id)
        if balance < price:
            invoice_titles = {
                CB_RELATIONSHIP: get_text(lang, "invoice_love_title"),
                CB_CAREER: get_text(lang, "invoice_career_title"),
            }
            invoice_descriptions = {
                CB_RELATIONSHIP: get_text(lang, "invoice_love_desc"),
                CB_CAREER: get_text(lang, "invoice_career_desc"),
            }
            await send_stars_invoice(
                callback=callback,
                title=invoice_titles.get(
                    callback.data, get_text(lang, "invoice_default_title")
                ),
                description=invoice_descriptions.get(
                    callback.data, get_text(lang, "invoice_default_desc")
                ),
                amount_stars=price,
                payload=f"topup:{price}",
            )
            return

        try:
            await increment_balance(db, callback.from_user.id, -price)
        except InsufficientBalanceError:
            if callback.message:
                await callback.message.answer(get_text(lang, "error_payment"))
            return

    await state.set_state(TarotForm.question)
    await state.update_data(reading_type=callback.data, price=price)

    if callback.message:
        await callback.message.answer(
            get_text(lang, "ask_question_tarot"), reply_markup=back_to_menu_kb(lang)
        )


async def tarot_reading_process(
    event: types.Message | types.CallbackQuery, state: FSMContext, db: firestore.Client
) -> None:
    """Спільна логіка для обробки запиту (після введення питання або для Карти дня)."""
    user_id = event.from_user.id
    is_message = isinstance(event, types.Message)
    target_message = event if is_message else event.message
    if not target_message:
        return

    lang = await get_user_language(db, user_id)
    data = await state.get_data()
    price = data.get("price", 0)
    reading_type = data.get("reading_type", CB_DAILY)

    # Для "Карти дня" питання не потрібне, використовуємо стандартне
    if reading_type == CB_DAILY:
        user_question = get_text(lang, "daily_card_question")
    else:
        user_question = event.text if is_message else ""
        if not user_question:  # Якщо користувач не ввів питання
            user_question = get_text(lang, "default_tarot_request")

    # Анімація завантаження
    loading_msg = await target_message.answer(
        get_text(lang, "loading_tarot"), parse_mode="HTML"
    )

    # Динамічно отримуємо системну інструкцію
    system_instruction = get_text(lang, "karma_system_prompt")

    # Отримуємо модель з контексту, переданого через workflow_data
    dp = Dispatcher.get_current()
    tarot_model = dp.workflow_data.get("tarot_model")

    # Генеруємо відповідь
    text = await _gemini_text(tarot_model, user_question, system_instruction)

    await loading_msg.delete()  # Видаляємо повідомлення "малюю"

    if not text:
        is_admin = user_id in ADMIN_IDS
        refund_note = ""
        if not is_admin and price > 0:
            try:
                await increment_balance(db, user_id, price)
                refund_note = get_text(lang, "refund_note").format(price=price)
            except:  # noqa: E722
                pass
        silent_msg = get_text(lang, "tarot_silent")
        await target_message.answer(
            f"{silent_msg} {refund_note}".strip(),
            reply_markup=main_menu_kb(lang),
            parse_mode="HTML",
        )
        await state.clear()
        return

    # Обираємо правильну картинку
    lang_images = IMAGES_TAROT.get(lang, IMAGES_TAROT["uk"])
    image_url = lang_images.get(reading_type, "")

    caption_keys = {
        CB_DAILY: "daily_card_caption",
        CB_RELATIONSHIP: "love_reading_caption",
        CB_CAREER: "career_reading_caption",
    }
    caption = get_text(lang, caption_keys.get(reading_type, ""))

    # Відправляємо результат
    await target_message.answer_photo(photo=image_url, caption=caption, parse_mode="HTML")
    await target_message.answer(text, parse_mode="HTML")
    await target_message.answer(
        get_text(lang, "more_action_btn"),
        reply_markup=main_menu_kb(lang),
        parse_mode="HTML",
    )

    await state.clear()


@router.message(TarotForm.question)
async def message_tarot_process_wrapper(
    message: types.Message, state: FSMContext, db: firestore.Client
):
    await tarot_reading_process(message, state, db)
