import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from firebase_admin import firestore

from firebase_db import ensure_user, update_user_language
from keyboards import (
    CB_BACK_MENU,
    CB_CHANGE_ZODIAC,
    CB_PROFILE,
    CB_SHARE_HOROSCOPE,
    language_selection_kb,
    main_menu_kb,
    zodiac_selection_kb,
)
from lexicon import get_text

router = Router()

_SHARE_EMPTY = {
    "uk": "Поки ще немає гороскопу для поширення.",
    "en": "There is no horoscope to share yet.",
    "ru": "Пока еще нет гороскопа для пересылки.",
}

_SHARE_READY = {
    "uk": "Готово! Надсилаю текст для пересилання.",
    "en": "Done. Sending a ready-to-forward message.",
    "ru": "Готово! Отправляю текст для пересылки.",
}

_SHARE_FOOTER = {
    "uk": "✨ <i>Перешли це повідомлення друзям.</i>",
    "en": "✨ <i>Forward this message to your friends.</i>",
    "ru": "✨ <i>Перешли это сообщение друзьям.</i>",
}


def _share_map(mapping: dict[str, str], lang: str) -> str:
    return mapping.get(lang, mapping["uk"])


@router.message(CommandStart())
async def command_start(message: Message, db: firestore.Client) -> None:
    if not message.from_user:
        return

    await ensure_user(
        db,
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
    )

    await message.answer(
        get_text("uk", "choose_language"),
        reply_markup=language_selection_kb(),
    )


@router.callback_query(F.data.startswith("set_lang:"))
async def process_language_selection(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user or not callback.message:
        return

    lang = callback.data.split(":")[1]
    await update_user_language(db, callback.from_user.id, lang)

    await callback.answer(get_text(lang, "lang_saved"))
    await callback.message.delete()

    user_name = callback.from_user.first_name or "душе"
    welcome_text = get_text(lang, "welcome_text").format(name=user_name)
    img_welcome = "https://i.postimg.cc/7hWHVtr6/Gemini_Generated_Image_y1ell9y1ell9y1el_(1).png"

    try:
        await callback.message.answer_photo(
            photo=img_welcome,
            caption=welcome_text,
            reply_markup=main_menu_kb(lang),
            parse_mode="HTML",
        )
    except Exception as e:
        logging.error("Welcome image send failed: %s", e)
        await callback.message.answer(
            text=welcome_text,
            reply_markup=main_menu_kb(lang),
            parse_mode="HTML",
        )


@router.callback_query(F.data == CB_PROFILE)
async def profile(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user:
        return

    user_id = str(callback.from_user.id)
    doc = db.collection("users").document(user_id).get()
    user_data = doc.to_dict() or {}

    lang = user_data.get("language", "uk")
    balance = user_data.get("balance", 0)
    current_zodiac = user_data.get("zodiac_sign", "all")

    zodiac_dict = get_text(lang, "zodiacs")
    zodiac_name = zodiac_dict.get(current_zodiac, zodiac_dict.get("all"))
    text = get_text(lang, "profile_text").format(balance=balance, zodiac=zodiac_name)

    profile_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, "btn_setup_horoscope"), callback_data=CB_CHANGE_ZODIAC)],
            [InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data=CB_BACK_MENU)],
        ]
    )

    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=profile_kb, parse_mode="HTML")
        except Exception:
            await callback.message.answer(text, reply_markup=profile_kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == CB_BACK_MENU)
async def back_to_menu_handler(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user:
        return

    user_id = str(callback.from_user.id)
    doc = db.collection("users").document(user_id).get()
    lang = doc.to_dict().get("language", "uk") if doc.exists else "uk"

    text = get_text(lang, "main_menu_title")
    kb = main_menu_kb(lang)

    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == CB_CHANGE_ZODIAC)
async def setup_zodiac(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user:
        return

    user_id = str(callback.from_user.id)
    doc = db.collection("users").document(user_id).get()
    lang = doc.to_dict().get("language", "uk") if doc.exists else "uk"

    text = get_text(lang, "zodiac_setup_title")
    kb = zodiac_selection_kb(lang)

    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("set_zodiac:"))
async def process_set_zodiac(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user:
        return

    zodiac = callback.data.split(":")[1]
    user_id = str(callback.from_user.id)

    db.collection("users").document(user_id).set({"zodiac_sign": zodiac}, merge=True)

    doc = db.collection("users").document(user_id).get()
    lang = doc.to_dict().get("language", "uk") if doc.exists else "uk"

    await callback.answer(get_text(lang, "zodiac_saved"))
    await profile(callback, db)


@router.callback_query(F.data == CB_SHARE_HOROSCOPE)
async def share_horoscope(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user or not callback.message:
        return

    user_id = str(callback.from_user.id)
    doc = db.collection("users").document(user_id).get()
    user_data = doc.to_dict() or {}
    lang = user_data.get("language", "uk")
    share_text = user_data.get("last_horoscope_share_text", "").strip()

    if not share_text:
        await callback.answer(_share_map(_SHARE_EMPTY, lang), show_alert=True)
        return

    await callback.answer(_share_map(_SHARE_READY, lang))
    await callback.message.answer(
        f"{share_text}\n\n{_share_map(_SHARE_FOOTER, lang)}",
        parse_mode="HTML",
    )