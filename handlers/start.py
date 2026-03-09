from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from firebase_admin import firestore
from firebase_db import update_user_language, get_user_language
from keyboards import language_selection_kb
from lexicon import get_text

# Додай сюди імпорт нових функцій:
from firebase_db import ensure_user, get_balance, update_user_zodiac
from keyboards import CB_BACK_MENU, CB_PROFILE, main_menu_kb, ZODIACS, zodiac_selection_kb, CB_CHANGE_ZODIAC



router = Router()

WELCOME_IMAGE_URL = "https://i.postimg.cc/7hWHVtr6/Gemini-Generated-Image-y1ell9y1ell9y1el-(1).png"


@router.message(CommandStart())
async def command_start(message: Message, db: firestore.Client) -> None:
    if not message.from_user: return
    
    # 👇 ТУТ ВИПРАВЛЕНО: додано user_id=, username=, first_name=
    await ensure_user(
        db, 
        user_id=message.from_user.id, 
        username=message.from_user.username or "", 
        first_name=message.from_user.first_name or ""
    )
    
    # Завжди при старті пропонуємо обрати мову (текст беремо одразу трьома мовами)
    await message.answer(
        get_text("uk", "choose_language"), 
        reply_markup=language_selection_kb()
    )

# 👇 ДОДАЄМО НОВИЙ ОБРОБНИК ДЛЯ КНОПОК МОВИ 👇
@router.callback_query(F.data.startswith("set_lang:"))
async def process_language_selection(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user: return
    
    # Витягуємо обрану мову (uk, en або ru)
    lang = callback.data.split(":")[1]
    
    # Зберігаємо в базу
    await update_user_language(db, callback.from_user.id, lang)
    
    # Відповідаємо спливаючим вікном на обраній мові
    await callback.answer(get_text(lang, "lang_saved"))
    
    # Видаляємо повідомлення з вибором мови і показуємо головне меню!
    await callback.message.delete()
    await callback.message.answer(
        "✨", # Тут пізніше зробимо гарне привітання різними мовами
        reply_markup=main_menu_kb(lang)
    )


@router.callback_query(F.data == CB_BACK_MENU)
async def back_to_menu(callback: CallbackQuery) -> None:
    # Кнопка "Назад" може видаляти старе повідомлення, щоб не засмічувати чат
    if callback.message:
        await callback.message.delete()
        await callback.message.answer("Головне меню:", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == CB_PROFILE)
async def profile(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user: return
    
    user_id = str(callback.from_user.id)
    doc = db.collection("users").document(user_id).get()
    user_data = doc.to_dict() or {}
    
    balance = user_data.get("balance", 0)
    current_zodiac = user_data.get("zodiac_sign", "all")
    zodiac_name = ZODIACS.get(current_zodiac, "🌌 Усі знаки")

    text = (
        f"<b>🧘 Твій енергетичний баланс:</b>\n"
        f"✨ Доступно зірок: <b>{balance} ⭐️</b>\n\n"
        f"🔮 <b>Твій знак Зодіаку:</b> {zodiac_name}\n\n"
        "<b>Як поповнити запаси?</b>\n"
        "У Всесвіті діє закон обміну. Просто обери будь-який платний розклад...\n\n"
        "<i>Енергія нікуди не зникає, вона лише змінює форму.</i>"
    )

    # Додаємо кнопку "Налаштувати гороскоп" прямо під профіль
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    profile_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔮 Налаштувати гороскоп", callback_data=CB_CHANGE_ZODIAC)],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data=CB_BACK_MENU)]
    ])

    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=profile_kb)
        except Exception:
            await callback.message.answer(text, reply_markup=profile_kb)
    await callback.answer()


# 👇 ДОДАЄМО ОБРОБНИКИ ДЛЯ ГОРОСКОПУ 👇

@router.callback_query(F.data == CB_CHANGE_ZODIAC)
async def change_zodiac_menu(callback: CallbackQuery) -> None:
    """Показує клавіатуру вибору знаку"""
    if callback.message:
        await callback.message.edit_text(
            "🔮 <b>Обери свій знак Зодіаку:</b>\n\n"
            "Якщо обереш конкретний знак, я надсилатиму гороскоп тільки для нього. "
            "Якщо обереш «Усі знаки» — отримуватимеш повний список, щоб ділитися з друзями!",
            reply_markup=zodiac_selection_kb()
        )
    await callback.answer()


@router.callback_query(F.data.startswith("set_zodiac:"))
async def process_zodiac_selection(callback: CallbackQuery, db: firestore.Client) -> None:
    """Зберігає обраний знак у базу"""
    if not callback.from_user: return
    
    zodiac_key = callback.data.split(":")[1]
    await update_user_zodiac(db, callback.from_user.id, zodiac_key)
    
    zodiac_name = ZODIACS.get(zodiac_key, "🌌 Усі знаки")
    
    await callback.answer(f"✅ Твій знак змінено на: {zodiac_name}", show_alert=True)
    # Повертаємо в профіль
    await profile(callback, db)