from __future__ import annotations

import asyncio
import logging
import datetime
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from firebase_admin import firestore

from firebase_db import claim_ai_action_lock, get_user_language, log_chat_message, release_ai_action_lock, get_balance, increment_balance
from handlers.admin import ADMIN_IDS
from keyboards import back_to_menu_kb, matrix_upsell_kb, matrix_saved_dob_kb, CB_MATRIX_FINANCE, CB_MATRIX_LOVE, CB_MATRIX_CLOSE, CB_MATRIX_USE_SAVED, CB_MATRIX_BUY_SLOT
from lexicon import get_text
from utils.matrix_math import calculate_matrix
from utils.matrix_image import generate_matrix_image

router = Router()

CB_MATRIX = "matrix:start"
MATRIX_UPSELL_PRICE = 50

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

    doc = await asyncio.to_thread(lambda: db.collection("users").document(str(callback.from_user.id)).get())
    user_data = doc.to_dict() or {}
    saved_dob = user_data.get("matrix_dob")

    if saved_dob:
        text = get_text(lang, "matrix_intro_saved").format(dob=saved_dob)
        kb = matrix_saved_dob_kb(lang, saved_dob)
    else:
        text = get_text(lang, "matrix_intro")
        kb = back_to_menu_kb(lang)
    
    await callback.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()


async def _execute_saved_dob_logic(message: Message, clean_dob: str, user_id: int, state: FSMContext, db: firestore.Client, tarot_model: Any, lang: str):
    doc_ref = db.collection("users").document(str(user_id))
    doc = await asyncio.to_thread(lambda: doc_ref.get())
    user_data = doc.to_dict() or {}
    
    last_req = user_data.get("matrix_last_own_req")
    if last_req and user_id not in ADMIN_IDS:
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - last_req
        if diff.days < 3:
            await message.answer(get_text(lang, "matrix_limit_own"), parse_mode="HTML")
            return
            
    await asyncio.to_thread(lambda: doc_ref.set({"matrix_last_own_req": firestore.SERVER_TIMESTAMP}, merge=True))
    
    data = await state.get_data()
    action_key = data.get("action_key", "matrix_base")
    
    await _process_matrix_generation(message, clean_dob, user_id, state, db, tarot_model, lang, action_key)


@router.callback_query(F.data == CB_MATRIX_USE_SAVED, MatrixStates.waiting_for_dob)
async def use_saved_dob(callback: CallbackQuery, state: FSMContext, db: firestore.Client, tarot_model: Any) -> None:
    if not callback.from_user or not callback.message:
        return
        
    user_id = callback.from_user.id
    lang = await get_user_language(db, user_id)
    
    doc = await asyncio.to_thread(lambda: db.collection("users").document(str(user_id)).get())
    user_data = doc.to_dict() or {}
    clean_dob = user_data.get("matrix_dob")
    
    if not clean_dob:
        await callback.answer("Дані втрачено", show_alert=True)
        return
        
    await callback.answer()
    
    class FakeMessage:
        def __init__(self, msg, text):
            self._msg = msg
            self.from_user = msg.from_user
            self.text = text
        async def answer(self, *args, **kwargs):
            return await self._msg.answer(*args, **kwargs)
        async def answer_photo(self, *args, **kwargs):
            return await self._msg.answer_photo(*args, **kwargs)
            
    await _execute_saved_dob_logic(FakeMessage(callback.message, clean_dob), clean_dob, user_id, state, db, tarot_model, lang)


@router.message(MatrixStates.waiting_for_dob)
async def process_dob(message: Message, state: FSMContext, db: firestore.Client, tarot_model: Any) -> None:
    if not message.from_user or not message.text:
        return

    user_id = message.from_user.id
    lang = await get_user_language(db, user_id)
    dob_str = message.text.strip()

    try:
        parsed_date = datetime.datetime.strptime(dob_str, "%d.%m.%Y")
        if parsed_date.year < 1900 or parsed_date.year > datetime.datetime.now().year:
            raise ValueError("Year out of bounds")
        clean_dob = parsed_date.strftime("%d.%m.%Y")
    except ValueError:
        await message.answer(
            get_text(lang, "matrix_invalid_date"),
            reply_markup=back_to_menu_kb(lang),
            parse_mode="HTML"
        )
        return

    doc_ref = db.collection("users").document(str(user_id))
    doc = await asyncio.to_thread(lambda: doc_ref.get())
    user_data = doc.to_dict() or {}
    saved_dob = user_data.get("matrix_dob")

    if not saved_dob:
        # First time ever saving dob! It's free.
        await asyncio.to_thread(lambda: doc_ref.set({"matrix_dob": clean_dob}, merge=True))
        await _execute_saved_dob_logic(message, clean_dob, user_id, state, db, tarot_model, lang)
        return
    elif clean_dob == saved_dob:
        # Repeating their own date. Fallback to use_saved_dob logic (3 day limit).
        await _execute_saved_dob_logic(message, clean_dob, user_id, state, db, tarot_model, lang)
        return
    else:
        # Foreign date logic
        matrix_free_slots = int(user_data.get("matrix_free_slots", 2))
        if matrix_free_slots <= 0 and user_id not in ADMIN_IDS:
            from keyboards import matrix_limit_foreign_kb
            await message.answer(
                get_text(lang, "matrix_limit_foreign"),
                reply_markup=matrix_limit_foreign_kb(lang),
                parse_mode="HTML"
            )
            return
            
        # Consume slot
        await asyncio.to_thread(lambda: doc_ref.set({"matrix_free_slots": matrix_free_slots - 1}, merge=True))
        
        data = await state.get_data()
        action_key = data.get("action_key", "matrix_base")
        await _process_matrix_generation(message, clean_dob, user_id, state, db, tarot_model, lang, action_key)


async def _process_matrix_generation(message: Message, clean_dob: str, user_id: int, state: FSMContext, db: firestore.Client, tarot_model: Any, lang: str, action_key: str):
    processing_msg = await message.answer(get_text(lang, "matrix_processing"), parse_mode="HTML")

    prompt_lang_map = {
        "uk": "українською мовою",
        "en": "англійською мовою (in English)",
        "ru": "російською мовою"
    }
    prompt_lang = prompt_lang_map.get(lang, "українською мовою")

    try:
        matrix = calculate_matrix(clean_dob)
        
        # Зберігаємо результати у FSMContext для майбутніх платних кнопок
        await state.update_data(matrix=matrix, dob=clean_dob)

        # 1. Генерація зображення (Pillow)
        img_bytes = await asyncio.to_thread(generate_matrix_image, matrix, lang)

        # 2. Генерація тексту (Gemini)
        prompt = (
            f"Я розрахував Матрицю Долі для людини, яка народилася {clean_dob}.\n"
            f"Основні аркани:\n"
            f"- Портрет (як людину бачить соціум): Аркан {matrix['portrait']}\n"
            f"- Характер/Центр (основа особистості): Аркан {matrix['center']}\n\n"
            f"Напиши містичну, глибоку, але сучасну розшифровку цих двох енергій (Портрет і Характер). "
            f"Використовуй езотеричний, але зрозумілий стиль. Форматування має бути красивим, з емодзі. "
            f"Відповідай {prompt_lang}. Звертайся до людини на 'ти'. Обсяг: приблизно 200-250 слів."
        )

        response = await asyncio.to_thread(tarot_model.generate_content, prompt)
        reply_text = response.text

        if not reply_text:
            raise ValueError("Empty response from AI")

        # Надсилаємо картинку
        await message.answer_photo(BufferedInputFile(img_bytes, filename="matrix.png"))
        
        # Видаляємо проміжне повідомлення
        await processing_msg.delete()
        
        # Надсилаємо текст з кнопками Upsell
        await message.answer(reply_text, reply_markup=matrix_upsell_kb(lang), parse_mode="HTML")
        
        await log_chat_message(db, user_id, "user", f"[Matrix of Destiny DOB: {clean_dob}]")
        await log_chat_message(db, user_id, "bot", reply_text)

    except Exception as e:
        import logging
        logging.error(f"Matrix of Destiny error for user {user_id}: {e}", exc_info=True)
        await processing_msg.edit_text(
            get_text(lang, "error_energy_flows"),
            reply_markup=back_to_menu_kb(lang),
            parse_mode="HTML"
        )
    finally:
        await release_ai_action_lock(db, user_id)
        await state.set_state(None)


async def execute_matrix_upsell(user_id: int, message: Message, channel: str, dob: str, matrix: dict, db: firestore.Client, tarot_model: Any, lang: str):
    """
    Виконує безпосередню генерацію Upsell розбору (фінанси або стосунки).
    Викликається з handlers/matrix.py або з handlers/payment.py
    """
    action_key = f"matrix_upsell_{channel}"
    locked = await claim_ai_action_lock(db, user_id, action_key)
    if not locked:
        await message.answer(get_text(lang, "error_energy_flows"), parse_mode="HTML")
        return

    processing_msg = await message.answer(get_text(lang, "matrix_upsell_processing"), parse_mode="HTML")

    prompt_lang_map = {
        "uk": "українською мовою",
        "en": "англійською мовою (in English)",
        "ru": "російською мовою"
    }
    prompt_lang = prompt_lang_map.get(lang, "українською мовою")

    try:
        topic_key = "matrix_topic_finance" if channel == "finance" else "matrix_topic_love"
        topic = get_text(lang, topic_key)
        
        prompt = (
            f"Я розрахував Матрицю Долі для людини, яка народилася {dob}.\n"
            f"Аркани: Портрет {matrix.get('portrait')}, Талант {matrix.get('talent')}, "
            f"Карма {matrix.get('karma')}, Соціум {matrix.get('social')}, Центр {matrix.get('center')}.\n\n"
            f"Зроби глибокий аналіз {topic} на основі цих енергій. "
            f"Відповідай {prompt_lang}. Стиль: сучасна містика. Обсяг: приблизно 200-250 слів."
        )

        response = await asyncio.to_thread(tarot_model.generate_content, prompt)
        reply_text = response.text

        await processing_msg.edit_text(reply_text, reply_markup=matrix_upsell_kb(lang), parse_mode="HTML")
        
        await log_chat_message(db, user_id, "user", f"[Matrix Upsell {channel}]")
        await log_chat_message(db, user_id, "bot", reply_text)

    except Exception as e:
        logging.error(f"Matrix upsell error for user {user_id}: {e}", exc_info=True)
        await processing_msg.edit_text(get_text(lang, "error_energy_flows"), parse_mode="HTML")
        await increment_balance(db, user_id, MATRIX_UPSELL_PRICE) # Refund
    finally:
        await release_ai_action_lock(db, user_id, action_key)


@router.callback_query(F.data.in_([CB_MATRIX_FINANCE, CB_MATRIX_LOVE]))
async def handle_matrix_upsell(callback: CallbackQuery, state: FSMContext, db: firestore.Client, tarot_model: Any) -> None:
    if not callback.from_user or not callback.message:
        return
        
    user_id = callback.from_user.id
    lang = await get_user_language(db, user_id)
    
    data = await state.get_data()
    dob = data.get("dob")
    matrix = data.get("matrix")
    
    if not dob:
        doc = await asyncio.to_thread(lambda: db.collection("users").document(str(user_id)).get())
        user_data = doc.to_dict() or {}
        dob = user_data.get("matrix_dob")
        
    if not dob:
        await callback.answer(get_text(lang, "matrix_data_lost_alert"), show_alert=True)
        return
        
    if not matrix:
        matrix = calculate_matrix(dob)
        
    channel = "finance" if callback.data == CB_MATRIX_FINANCE else "love"
    
    from handlers.payment import send_stars_invoice
    
    balance = await get_balance(db, user_id)
    if balance < MATRIX_UPSELL_PRICE and user_id not in ADMIN_IDS:
        title_key = "matrix_btn_finance" if channel == "finance" else "matrix_btn_love"
        desc_key = "matrix_desc_finance" if channel == "finance" else "matrix_desc_love"
        await send_stars_invoice(
            callback=callback,
            title=get_text(lang, title_key),
            description=get_text(lang, desc_key),
            amount_stars=MATRIX_UPSELL_PRICE,
            payload=f"matrix:{channel}:{MATRIX_UPSELL_PRICE}"
        )
        return
        
    # Списуємо баланс (зроблено вручну, адміни безкоштовно)
    if user_id not in ADMIN_IDS:
        await increment_balance(db, user_id, -MATRIX_UPSELL_PRICE)
    
    # Прибираємо клавіатуру на поточному повідомленні
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
        
    await execute_matrix_upsell(user_id, callback.message, channel, dob, matrix, db, tarot_model, lang)
    await callback.answer()


@router.callback_query(F.data == CB_MATRIX_CLOSE)
async def matrix_close_handler(callback: CallbackQuery, db: firestore.Client, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return

    lang = await get_user_language(db, callback.from_user.id)
    
    # Прибираємо кнопку Назад, залишаємо канали
    try:
        await callback.message.edit_reply_markup(reply_markup=matrix_upsell_kb(lang, hide_back=True))
    except Exception:
        pass
        
    await state.clear()
    await release_ai_action_lock(db, callback.from_user.id)
    
    text = get_text(lang, "main_menu_title")
    from keyboards import main_menu_kb
    kb = main_menu_kb(lang)
    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == CB_MATRIX_BUY_SLOT)
async def handle_matrix_buy_slot(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user or not callback.message:
        return
        
    user_id = callback.from_user.id
    lang = await get_user_language(db, user_id)
    
    from handlers.payment import send_stars_invoice
    
    await send_stars_invoice(
        callback=callback,
        title=get_text(lang, "matrix_slot_title"),
        description=get_text(lang, "matrix_slot_desc"),
        amount_stars=15,
        payload="matrix_slot:15"
    )
    await callback.answer()
