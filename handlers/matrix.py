from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import google.generativeai as genai
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from firebase_admin import firestore

from config import primary_model_name
from firebase_db import claim_ai_action_lock, get_user_language, log_chat_message, release_ai_action_lock
from keyboards import back_to_menu_kb
from lexicon import get_text
from utils.matrix_math import calculate_matrix
from handlers.tarot import SAFETY_SETTINGS

router = Router()

CB_MATRIX = "matrix:start"


class MatrixStates(StatesGroup):
    waiting_for_dob = State()


@router.callback_query(F.data == CB_MATRIX)
async def start_matrix(callback: CallbackQuery, state: FSMContext, db: firestore.Client) -> None:
    if not callback.from_user or not callback.message:
        return

    lang = await get_user_language(db, callback.from_user.id)
    
    action_key = "matrix_base"
    locked = await claim_ai_action_lock(db, callback.from_user.id, action_key)
    if not locked:
        await callback.answer(get_text(lang, "error_energy_flows"), show_alert=True)
        return

    await state.set_state(MatrixStates.waiting_for_dob)
    await state.update_data(action_key=action_key)

    text = "🔮 <b>Матриця Долі</b>\n\nВведіть вашу дату народження у форматі <b>ДД.ММ.РРРР</b> (наприклад, 15.05.1995):"
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu_kb(lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(MatrixStates.waiting_for_dob)
async def process_dob(message: Message, state: FSMContext, db: firestore.Client) -> None:
    if not message.from_user or not message.text:
        return

    user_id = message.from_user.id
    lang = await get_user_language(db, user_id)
    dob_str = message.text.strip()

    # Валідація дати (захист від дурнів)
    try:
        parsed_date = datetime.strptime(dob_str, "%d.%m.%Y")
        if parsed_date.year < 1900 or parsed_date.year > datetime.now().year:
            raise ValueError("Year out of bounds")
        clean_dob = parsed_date.strftime("%d.%m.%Y")
    except ValueError:
        await message.answer(
            "⚠️ Неправильний формат дати. Будь ласка, використовуйте формат <b>ДД.ММ.РРРР</b> (наприклад, 15.05.1995).",
            reply_markup=back_to_menu_kb(lang),
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    action_key = data.get("action_key", "matrix_base")

    processing_msg = await message.answer("✨ Розраховую аркани та налаштовую зв'язок з Всесвітом...", parse_mode="HTML")

    try:
        matrix = calculate_matrix(clean_dob)
        
        # Зберігаємо результати у FSMContext для майбутніх платних кнопок (Етап 2)
        await state.update_data(matrix=matrix, dob=clean_dob)

        prompt = (
            f"Я розрахував Матрицю Долі для людини, яка народилася {clean_dob}.\n"
            f"Основні аркани:\n"
            f"- Портрет (як людину бачить соціум): Аркан {matrix['portrait']}\n"
            f"- Характер/Центр (основа особистості): Аркан {matrix['center']}\n\n"
            f"Напиши містичну, глибоку, але сучасну розшифровку цих двох енергій (Портрет і Характер). "
            f"Використовуй езотеричний, але зрозумілий стиль. Форматування має бути красивим, з емодзі. "
            f"Відповідай українською мовою. Звертайся до людини на 'ти'. Обсяг: приблизно 200-250 слів."
        )

        model = genai.GenerativeModel(primary_model_name, safety_settings=SAFETY_SETTINGS)
        response = await asyncio.to_thread(model.generate_content, prompt)
        reply_text = response.text

        if not reply_text:
            raise ValueError("Empty response from AI")

        await processing_msg.edit_text(reply_text, reply_markup=back_to_menu_kb(lang), parse_mode="HTML")
        await log_chat_message(db, user_id, "user", f"[Matrix of Destiny DOB: {clean_dob}]")
        await log_chat_message(db, user_id, "bot", reply_text)

    except Exception as e:
        logging.error(f"Matrix of Destiny error for user {user_id}: {e}", exc_info=True)
        await processing_msg.edit_text(
            get_text(lang, "error_energy_flows"),
            reply_markup=back_to_menu_kb(lang),
            parse_mode="HTML"
        )
    finally:
        await release_ai_action_lock(db, user_id)
        await state.set_state(None)
