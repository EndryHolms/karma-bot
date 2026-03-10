import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from firebase_admin import firestore

from firebase_db import REFERRAL_DAILY_BONUS, bind_referrer, ensure_user, update_user_language
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

CB_INVITE_FRIEND = "profile:invite"

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

_PROFILE_TEXT = {
    "uk": (
        "<b>👤 Моя карма</b>\n\n"
        "⭐ <b>Енергетичний баланс:</b> {balance} ⭐\n"
        "🎁 <b>Бонуси за друзів:</b> {referral_rewards_total} ⭐\n"
        "👥 <b>Запрошено друзів:</b> {referrals_count}\n"
        "🔮 <b>Твій знак:</b> {zodiac}\n\n"
        "<i>Запрошуй друзів і відкривай карту дня, щоб накопичувати енергію для нових розкладів.</i>"
    ),
    "en": (
        "<b>👤 My Karma</b>\n\n"
        "⭐ <b>Energy balance:</b> {balance} ⭐\n"
        "🎁 <b>Friend bonuses:</b> {referral_rewards_total} ⭐\n"
        "👥 <b>Invited friends:</b> {referrals_count}\n"
        "🔮 <b>Your sign:</b> {zodiac}\n\n"
        "<i>Invite friends and open your card of the day to collect more energy for new readings.</i>"
    ),
    "ru": (
        "<b>👤 Моя карма</b>\n\n"
        "⭐ <b>Энергетический баланс:</b> {balance} ⭐\n"
        "🎁 <b>Бонусы за друзей:</b> {referral_rewards_total} ⭐\n"
        "👥 <b>Приглашено друзей:</b> {referrals_count}\n"
        "🔮 <b>Твой знак:</b> {zodiac}\n\n"
        "<i>Приглашай друзей и открывай карту дня, чтобы накапливать энергию для новых раскладов.</i>"
    ),
}

_INVITE_BUTTON = {
    "uk": "🎁 Запросити друга",
    "en": "🎁 Invite a friend",
    "ru": "🎁 Пригласить друга",
}

_REFERRAL_SCREEN = {
    "uk": (
        "<b>🎁 Запроси друга в Karma</b>\n\n"
        "Поділися своїм персональним запрошенням.\n\n"
        "Коли твій друг зайде в бот і відкриє свою <b>першу Карту Дня</b>, ти отримаєш <b>{bonus} ⭐ бонус</b> на нові розклади.\n\n"
        "<i>Чим більше друзів увійдуть у потік Karma, тим більше енергії повернеться до тебе.</i>\n\n"
        "<b>Твоє запрошення:</b>\n<code>{link}</code>\n\n"
        "<b>Готовий текст для пересилки:</b>\n{share_text}"
    ),
    "en": (
        "<b>🎁 Invite a friend to Karma</b>\n\n"
        "Share your personal invite link.\n\n"
        "When your friend opens the bot and reveals their <b>first Card of the Day</b>, you will receive a <b>{bonus} ⭐ bonus</b> for new readings.\n\n"
        "<i>The more friends enter the Karma flow, the more energy comes back to you.</i>\n\n"
        "<b>Your invite:</b>\n<code>{link}</code>\n\n"
        "<b>Ready-to-forward text:</b>\n{share_text}"
    ),
    "ru": (
        "<b>🎁 Пригласи друга в Karma</b>\n\n"
        "Поделись своей персональной ссылкой-приглашением.\n\n"
        "Когда твой друг зайдет в бота и откроет свою <b>первую Карту Дня</b>, ты получишь <b>{bonus} ⭐ бонус</b> на новые расклады.\n\n"
        "<i>Чем больше друзей войдут в поток Karma, тем больше энергии вернется к тебе.</i>\n\n"
        "<b>Твое приглашение:</b>\n<code>{link}</code>\n\n"
        "<b>Готовый текст для пересылки:</b>\n{share_text}"
    ),
}

_REFERRAL_SHARE_TEXT = {
    "uk": "✨ Я користуюсь Karma — ботом для карти дня, гороскопів і розкладів. Спробуй теж: {link}",
    "en": "✨ I use Karma — a bot for the Card of the Day, horoscopes, and readings. Try it too: {link}",
    "ru": "✨ Я пользуюсь Karma — ботом для карты дня, гороскопов и раскладов. Попробуй тоже: {link}",
}


def _localized(mapping: dict[str, str], lang: str) -> str:
    return mapping.get(lang, mapping["uk"])


def _extract_referrer_id(message: Message) -> int | None:
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None
    payload = parts[1].strip()
    if not payload.startswith("ref_"):
        return None
    raw_id = payload[4:]
    if not raw_id.isdigit():
        return None
    return int(raw_id)


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

    referrer_id = _extract_referrer_id(message)
    if referrer_id:
        await bind_referrer(db, message.from_user.id, referrer_id)

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
    balance = int(user_data.get("balance", 0) or 0)
    current_zodiac = user_data.get("zodiac_sign", "all")
    referral_rewards_total = int(user_data.get("referral_rewards_total", 0) or 0)
    referrals_count = int(user_data.get("referrals_count", 0) or 0)

    zodiac_dict = get_text(lang, "zodiacs")
    zodiac_name = zodiac_dict.get(current_zodiac, zodiac_dict.get("all"))
    text = _localized(_PROFILE_TEXT, lang).format(
        balance=balance,
        referral_rewards_total=referral_rewards_total,
        referrals_count=referrals_count,
        zodiac=zodiac_name,
    )

    profile_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_localized(_INVITE_BUTTON, lang), callback_data=CB_INVITE_FRIEND)],
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


@router.callback_query(F.data == CB_INVITE_FRIEND)
async def invite_friend(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user or not callback.message:
        return

    user_id = str(callback.from_user.id)
    doc = db.collection("users").document(user_id).get()
    user_data = doc.to_dict() or {}
    lang = user_data.get("language", "uk")

    me = await callback.bot.get_me()
    if not me.username:
        await callback.answer("Bot username is not configured.", show_alert=True)
        return

    link = f"https://t.me/{me.username}?start=ref_{callback.from_user.id}"
    share_text = _localized(_REFERRAL_SHARE_TEXT, lang).format(link=link)
    text = _localized(_REFERRAL_SCREEN, lang).format(
        bonus=REFERRAL_DAILY_BONUS,
        link=link,
        share_text=share_text,
    )

    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=get_text(lang, "btn_back_profile"), callback_data=CB_PROFILE)]]
    )

    await callback.message.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
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
        await callback.answer(_localized(_SHARE_EMPTY, lang), show_alert=True)
        return

    await callback.answer(_localized(_SHARE_READY, lang))
    await callback.message.answer(
        f"{share_text}\n\n{_localized(_SHARE_FOOTER, lang)}",
        parse_mode="HTML",
    )