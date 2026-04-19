from __future__ import annotations

import asyncio
import os
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from firebase_admin import firestore
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from firebase_db import (
    InsufficientBalanceError,
    claim_ai_action_lock,
    ensure_user,
    get_balance,
    get_user_language,
    increment_balance,
    log_chat_message,
    release_ai_action_lock,
)
from handlers.payment import send_stars_invoice
from keyboards import CB_ADVICE, back_to_menu_kb, main_menu_kb
from lexicon import get_text

router = Router()

ADVICE_PRICE = 25

_admin_env = os.getenv("ADMIN_IDS", "469764985")
ADMIN_IDS = [int(x.strip()) for x in _admin_env.split(",") if x.strip().isdigit()]

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

IMAGES_ADVICE = {
    "uk": "https://i.postimg.cc/qvxpMPwf/b-A-richly-detailed-Ta-4.png",
    "en": "https://i.postimg.cc/qvxpMPwf/b-A-richly-detailed-Ta-4.png",
    "ru": "https://i.postimg.cc/qvxpMPwf/b-A-richly-detailed-Ta-4.png",
}

ADVICE_HEADING_GUIDE = {
    "uk": {
        "symbol": "Символ",
        "wisdom": "Мудрість",
        "action": "Дія",
    },
    "en": {
        "symbol": "Symbol",
        "wisdom": "Wisdom",
        "action": "Action",
    },
    "ru": {
        "symbol": "Символ",
        "wisdom": "Мудрость",
        "action": "Действие",
    },
}


class AdviceStates(StatesGroup):
    waiting_for_question = State()


def _advice_heading_guide(lang: str) -> dict[str, str]:
    return ADVICE_HEADING_GUIDE.get(lang, ADVICE_HEADING_GUIDE["uk"])


def _advice_format_prompt(lang: str, target_language: str) -> str:
    headings = _advice_heading_guide(lang)
    return (
        f"Write the entire response only in {target_language}. Do not mix languages. "
        f"Use Telegram HTML only. Do not use Markdown. "
        f"Keep the emojis exactly as shown. Keep exactly one empty line after each heading and one empty line between blocks. "
        f"Return the answer in exactly this structure:\n\n"
        f"🌌 <b>{headings['symbol']}:</b>\n\n"
        f"[text]\n\n"
        f"🗝 <b>{headings['wisdom']}:</b>\n\n"
        f"[text]\n\n"
        f"⚡️ <b>{headings['action']}:</b>\n\n"
        f"[text]"
    )


async def _gemini_text(model: Any, prompt: str) -> str:
    def _sync() -> str:
        try:
            resp = model.generate_content(prompt, safety_settings=SAFETY_SETTINGS)
            if not resp or not hasattr(resp, "candidates") or not resp.candidates:
                return ""
            return resp.text.strip()
        except Exception as e:
            print(f"Advice Gen Error: {e}")
            return ""

    return await asyncio.to_thread(_sync)


@router.callback_query(F.data == CB_ADVICE)
async def ask_advice_start(callback: CallbackQuery, state: FSMContext, db: firestore.Client) -> None:
    if not callback.from_user:
        return
    await ensure_user(
        db,
        user_id=callback.from_user.id,
        username=callback.from_user.username or "",
        first_name=callback.from_user.first_name or "",
    )

    lang = await get_user_language(db, callback.from_user.id)
    action_key = "advice"
    if not await claim_ai_action_lock(db, callback.from_user.id, action_key):
        await callback.answer(get_text(lang, "magic_wait"), show_alert=True)
        return

    await callback.answer()
    is_admin = callback.from_user.id in ADMIN_IDS

    if not is_admin:
        balance = await get_balance(db, callback.from_user.id)
        if balance < ADVICE_PRICE:
            await release_ai_action_lock(db, callback.from_user.id, action_key)
            await send_stars_invoice(
                callback=callback,
                title=get_text(lang, "invoice_advice_title"),
                description=get_text(lang, "invoice_advice_desc"),
                amount_stars=ADVICE_PRICE,
                payload=f"topup:{ADVICE_PRICE}",
            )
            return

        try:
            await increment_balance(db, callback.from_user.id, -ADVICE_PRICE)
        except InsufficientBalanceError:
            if callback.message:
                await callback.message.answer(get_text(lang, "error_payment"))
            await release_ai_action_lock(db, callback.from_user.id, action_key)
            return

    await state.set_state(AdviceStates.waiting_for_question)
    await state.update_data(price=ADVICE_PRICE, action_key=action_key)

    if callback.message:
        await callback.message.answer(
            get_text(lang, "ask_question"),
            reply_markup=back_to_menu_kb(lang),
        )


@router.message(AdviceStates.waiting_for_question)
async def advice_process(message: Message, state: FSMContext, advice_model: Any, db: firestore.Client) -> None:
    if not message.from_user:
        return

    lang = await get_user_language(db, message.from_user.id)
    user_text = message.text or get_text(lang, "default_advice_request")

    data = await state.get_data()
    action_key = data.get("action_key", "advice")
    price = data.get("price", 1)

    msg = await message.answer(get_text(lang, "loading_advice"), reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")

    ai_languages = {"uk": "Ukrainian", "en": "English", "ru": "Russian"}
    target_language = ai_languages.get(lang, "Ukrainian")
    format_prompt = _advice_format_prompt(lang, target_language)
    prompt = (
        f"The user's request is: {user_text}. Give a deep, philosophical, but practical answer. "
        f"Use vivid imagery and stay concrete. "
        + format_prompt
    )

    text = await _gemini_text(advice_model, prompt)

    await msg.delete()

    if not text:
        is_admin = message.from_user.id in ADMIN_IDS
        refund_note = ""
        if not is_admin:
            try:
                await increment_balance(db, message.from_user.id, price)
                refund_note = get_text(lang, "refund_note").format(price=price)
            except Exception:
                pass

        silent_msg = get_text(lang, "universe_silent")
        await message.answer(f"{silent_msg} {refund_note}".strip(), reply_markup=main_menu_kb(lang), parse_mode="HTML")
        await release_ai_action_lock(db, message.from_user.id, action_key)
        await state.clear()
        return

    current_img = IMAGES_ADVICE.get(lang, IMAGES_ADVICE["uk"])
    await message.answer_photo(photo=current_img, caption=get_text(lang, "universe_answer"), parse_mode="HTML")

    await message.answer(text, parse_mode="HTML")
    await log_chat_message(db, message.from_user.id, "bot", text)
    await message.answer(get_text(lang, "more_action_btn"), reply_markup=main_menu_kb(lang), parse_mode="HTML")
    await release_ai_action_lock(db, message.from_user.id, action_key)
    await state.clear()
