import logging
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from firebase_admin import firestore

from firebase_db import ensure_user, get_user_language, update_user_language
from lexicon import get_text
from keyboards import (
    language_selection_kb, main_menu_kb, back_to_menu_kb, 
    zodiac_selection_kb, CB_PROFILE, CB_BACK_MENU, CB_CHANGE_ZODIAC
)

router = Router()

@router.message(CommandStart())
async def command_start(message: Message, db: firestore.Client) -> None:
    if not message.from_user: return
    
    await ensure_user(
        db, 
        user_id=message.from_user.id, 
        username=message.from_user.username or "", 
        first_name=message.from_user.first_name or ""
    )
    
    await message.answer(
        get_text("uk", "choose_language"), 
        reply_markup=language_selection_kb()
    )

@router.callback_query(F.data.startswith("set_lang:"))
async def process_language_selection(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user: return
    
    lang = callback.data.split(":")[1]
    await update_user_language(db, callback.from_user.id, lang)
    
    await callback.answer(get_text(lang, "lang_saved"))
    await callback.message.delete()
    
    user_name = callback.from_user.first_name or "душе"
    welcome_text = get_text(lang, "welcome_text").format(name=user_name)
    
    # 👇 ВСТАВ СЮДИ ПОСИЛАННЯ НА СВОЮ ОРИГІНАЛЬНУ КАРТИНКУ ПРИВІТАННЯ 👇
    IMG_WELCOME = "https://i.postimg.cc/7hWHVtr6/Gemini_Generated_Image_y1ell9y1ell9y1el_(1).png" 
    
    await callback.message.answer_photo(
        photo=IMG_WELCOME,
        caption=welcome_text,
        reply_markup=main_menu_kb(lang),
        parse_mode="HTML"
    )

@router.callback_query(F.data == CB_PROFILE)
async def profile(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user: return
    
    user_id = str(callback.from_user.id)
    doc = db.collection("users").document(user_id).get()
    user_data = doc.to_dict() or {}
    
    lang = user_data.get("language", "uk")
    balance = user_data.get("balance", 0)
    current_zodiac = user_data.get("zodiac_sign", "all")
    
    zodiac_dict = get_text(lang, "zodiacs")
    zodiac_name = zodiac_dict.get(current_zodiac, zodiac_dict.get("all"))

    text = get_text(lang, "profile_text").format(balance=balance, zodiac=zodiac_name)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    profile_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, "btn_setup_horoscope"), callback_data=CB_CHANGE_ZODIAC)],
        [InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data=CB_BACK_MENU)]
    ])

    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=profile_kb, parse_mode="HTML")
        except Exception:
            await callback.message.answer(text, reply_markup=profile_kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == CB_BACK_MENU)
async def back_to_menu_handler(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user: return
    
    lang = await get_user_language(db, callback.from_user.id)
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
    if not callback.from_user: return
    
    lang = await get_user_language(db, callback.from_user.id)
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
    if not callback.from_user: return
    
    zodiac = callback.data.split(":")[1]
    user_id = str(callback.from_user.id)
    
    db.collection("users").document(user_id).set({"zodiac_sign": zodiac}, merge=True)
    
    lang = await get_user_language(db, callback.from_user.id)
    await callback.answer(get_text(lang, "zodiac_saved"))
    
    await profile(callback, db)