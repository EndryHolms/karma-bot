import logging
from urllib.parse import urlencode

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from firebase_admin import firestore

from firebase_db import (
    REFERRAL_DAILY_BONUS,
    bind_referrer,
    ensure_user,
    release_ai_action_lock,
    update_horoscope_enabled,
    update_user_language,
    update_user_zodiac,
    log_chat_message,
)
from keyboards import (
    CB_BACK_MENU,
    CB_CHANGE_ZODIAC,
    CB_PROFILE,
    language_selection_kb,
    main_menu_kb,
)
from lexicon import get_text

router = Router()

CB_INVITE_FRIEND = "profile:invite"
CB_CHANGE_LANGUAGE = "profile:language"
CB_TOGGLE_HOROSCOPE = "profile:toggle_horoscope"
LANG_PROFILE_PREFIX = "set_lang_profile"

_PROFILE_TEXT = {
    "uk": (
        "<b>👤 Моя карма</b>\n\n"
        "<b>Твоя енергія</b>\n"
        "⭐ Баланс: <b>{balance} ⭐</b>\n"
        "🎁 Бонуси за друзів: <b>{referral_rewards_total} ⭐</b>\n\n"
        "<b>Твій профіль</b>\n"
        "👥 Запрошено друзів: <b>{referrals_count}</b>\n"
        "🔮 Знак: <b>{zodiac}</b>\n\n"
        "<i>Запрошуй друзів і відкривай карту дня,\n"
        "щоб накопичувати енергію для нових розкладів.</i>"
    ),
    "en": (
        "<b>👤 My Karma</b>\n\n"
        "<b>Your energy</b>\n"
        "⭐ Balance: <b>{balance} ⭐</b>\n"
        "🎁 Friend bonuses: <b>{referral_rewards_total} ⭐</b>\n\n"
        "<b>Your profile</b>\n"
        "👥 Invited friends: <b>{referrals_count}</b>\n"
        "🔮 Sign: <b>{zodiac}</b>\n\n"
        "<i>Invite friends and open your card of the day\n"
        "to collect more energy for new readings.</i>"
    ),
    "ru": (
        "<b>👤 Моя карма</b>\n\n"
        "<b>Твоя энергия</b>\n"
        "⭐ Баланс: <b>{balance} ⭐</b>\n"
        "🎁 Бонусы за друзей: <b>{referral_rewards_total} ⭐</b>\n\n"
        "<b>Твой профиль</b>\n"
        "👥 Приглашено друзей: <b>{referrals_count}</b>\n"
        "🔮 Знак: <b>{zodiac}</b>\n\n"
        "<i>Приглашай друзей и открывай карту дня,\n"
        "чтобы накапливать энергию для новых раскладов.</i>"
    ),
}

_INVITE_BUTTON = {
    "uk": "🎁 Запросити друга",
    "en": "🎁 Invite a friend",
    "ru": "🎁 Пригласить друга",
}

_LANGUAGE_BUTTON = {
    "uk": "🌐 Змінити мову",
    "en": "🌐 Change language",
    "ru": "🌐 Сменить язык",
}

_SEND_INVITE_BUTTON = {
    "uk": "📨 Надіслати другу запрошення",
    "en": "📨 Send invite to a friend",
    "ru": "📨 Отправить другу приглашение",
}

_LANGUAGE_PROMPT = {
    "uk": "🌐 <b>Оберіть мову</b>",
    "en": "🌐 <b>Choose your language</b>",
    "ru": "🌐 <b>Выберите язык</b>",
}

_HOROSCOPE_SETTINGS_TEXT = {
    "uk": (
        "🔮 <b>Налаштування гороскопу</b>\n\n"
        "<b>Твій знак:</b> {zodiac}\n"
        "<b>Щоденна розсилка:</b> {status}\n\n"
        "<i>Обери знак для персонального гороскопу або вимкни щоденну розсилку, якщо хочеш отримувати менше повідомлень.</i>"
    ),
    "en": (
        "🔮 <b>Horoscope settings</b>\n\n"
        "<b>Your sign:</b> {zodiac}\n"
        "<b>Daily delivery:</b> {status}\n\n"
        "<i>Choose your sign for a personal horoscope or turn off the daily delivery if you want fewer messages.</i>"
    ),
    "ru": (
        "🔮 <b>Настройки гороскопа</b>\n\n"
        "<b>Твой знак:</b> {zodiac}\n"
        "<b>Ежедневная рассылка:</b> {status}\n\n"
        "<i>Выбери знак для персонального гороскопа или выключи ежедневную рассылку, если хочешь получать меньше сообщений.</i>"
    ),
}

_HOROSCOPE_STATUS = {
    "uk": {True: "Увімкнено", False: "Вимкнено"},
    "en": {True: "Enabled", False: "Disabled"},
    "ru": {True: "Включена", False: "Выключена"},
}

_HOROSCOPE_TOGGLE_BUTTON = {
    "uk": {True: "🔕 Вимкнути щоденний гороскоп", False: "🔔 Увімкнути щоденний гороскоп"},
    "en": {True: "🔕 Turn off daily horoscope", False: "🔔 Turn on daily horoscope"},
    "ru": {True: "🔕 Выключить ежедневный гороскоп", False: "🔔 Включить ежедневный гороскоп"},
}

_REFERRAL_SCREEN = {
    "uk": (
        "<b>🎁 Запроси друга в Karma</b>\n\n"
        "Поділися своїм персональним запрошенням.\n\n"
        "Коли твій друг зайде в бот і відкриє свою <b>першу Карту Дня</b>, "
        "ти отримаєш <b>{bonus} ⭐ бонус</b> на нові розклади.\n\n"
        "<i>Чим більше друзів увійдуть у потік Karma, тим більше енергії повернеться до тебе.</i>\n\n"
        "<b>Твоє запрошення:</b>\n<code>{link}</code>\n\n"
        "<b>Готовий текст для пересилки:</b>\n{share_text}"
    ),
    "en": (
        "<b>🎁 Invite a friend to Karma</b>\n\n"
        "Share your personal invite link.\n\n"
        "When your friend opens the bot and reveals their <b>first Card of the Day</b>, "
        "you will receive a <b>{bonus} ⭐ bonus</b> for new readings.\n\n"
        "<i>The more friends enter the Karma flow, the more energy comes back to you.</i>\n\n"
        "<b>Your invite:</b>\n<code>{link}</code>\n\n"
        "<b>Ready-to-forward text:</b>\n{share_text}"
    ),
    "ru": (
        "<b>🎁 Пригласи друга в Karma</b>\n\n"
        "Поделись своей персональной ссылкой-приглашением.\n\n"
        "Когда твой друг зайдет в бота и откроет свою <b>первую Карту Дня</b>, "
        "ты получишь <b>{bonus} ⭐ бонус</b> на новые расклады.\n\n"
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

_REFERRAL_SHARE_PROMPT = {
    "uk": "Я користуюсь Karma — ботом для карти дня, гороскопів і розкладів. Спробуй теж.",
    "en": "I use Karma — a bot for the Card of the Day, horoscopes, and readings. Try it too.",
    "ru": "Я пользуюсь Karma — ботом для карты дня, гороскопов и раскладов. Попробуй тоже.",
}

_USERNAME_MISSING = {
    "uk": "Не вдалося сформувати посилання-запрошення.",
    "en": "Could not build the invite link.",
    "ru": "Не удалось сформировать ссылку-приглашение.",
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


def _horoscope_status_text(lang: str, enabled: bool) -> str:
    statuses = _HOROSCOPE_STATUS.get(lang, _HOROSCOPE_STATUS["uk"])
    return statuses[enabled]


def _horoscope_toggle_text(lang: str, enabled: bool) -> str:
    labels = _HOROSCOPE_TOGGLE_BUTTON.get(lang, _HOROSCOPE_TOGGLE_BUTTON["uk"])
    return labels[enabled]


def _horoscope_settings_text(lang: str, zodiac: str, enabled: bool) -> str:
    return _localized(_HOROSCOPE_SETTINGS_TEXT, lang).format(
        zodiac=zodiac,
        status=_horoscope_status_text(lang, enabled),
    )


def _horoscope_settings_kb(lang: str, enabled: bool) -> InlineKeyboardMarkup:
    z = get_text(lang, "zodiacs")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=z["aries"], callback_data="set_zodiac:aries"),
                InlineKeyboardButton(text=z["taurus"], callback_data="set_zodiac:taurus"),
                InlineKeyboardButton(text=z["gemini"], callback_data="set_zodiac:gemini"),
            ],
            [
                InlineKeyboardButton(text=z["cancer"], callback_data="set_zodiac:cancer"),
                InlineKeyboardButton(text=z["leo"], callback_data="set_zodiac:leo"),
                InlineKeyboardButton(text=z["virgo"], callback_data="set_zodiac:virgo"),
            ],
            [
                InlineKeyboardButton(text=z["libra"], callback_data="set_zodiac:libra"),
                InlineKeyboardButton(text=z["scorpio"], callback_data="set_zodiac:scorpio"),
                InlineKeyboardButton(text=z["sagittarius"], callback_data="set_zodiac:sagittarius"),
            ],
            [
                InlineKeyboardButton(text=z["capricorn"], callback_data="set_zodiac:capricorn"),
                InlineKeyboardButton(text=z["aquarius"], callback_data="set_zodiac:aquarius"),
                InlineKeyboardButton(text=z["pisces"], callback_data="set_zodiac:pisces"),
            ],
            [InlineKeyboardButton(text=get_text(lang, "btn_all_signs"), callback_data="set_zodiac:all")],
            [InlineKeyboardButton(text=_horoscope_toggle_text(lang, enabled), callback_data=CB_TOGGLE_HOROSCOPE)],
            [InlineKeyboardButton(text=get_text(lang, "btn_back_profile"), callback_data=CB_PROFILE)],
        ]
    )


async def _render_horoscope_settings(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user or not callback.message:
        return

    user_id = str(callback.from_user.id)
    doc = db.collection("users").document(user_id).get()
    user_data = doc.to_dict() or {}
    lang = user_data.get("language", "uk")
    enabled = bool(user_data.get("horoscope_enabled", True))
    current_zodiac = user_data.get("zodiac_sign", "all")
    zodiac_dict = get_text(lang, "zodiacs")
    zodiac_name = zodiac_dict.get(current_zodiac, zodiac_dict.get("all"))
    text = _horoscope_settings_text(lang, zodiac_name, enabled)
    kb = _horoscope_settings_kb(lang, enabled)

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")


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
@router.callback_query(F.data.startswith(f"{LANG_PROFILE_PREFIX}:"))
async def process_language_selection(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user or not callback.message:
        return

    callback_prefix, lang = callback.data.split(":", 1)
    await update_user_language(db, callback.from_user.id, lang)
    await callback.answer(get_text(lang, "lang_saved"))

    if callback_prefix == LANG_PROFILE_PREFIX:
        await profile(callback, db)
        return

    current_text = callback.message.text or callback.message.caption or ""
    lowered = current_text.lower()
    choose_language_markers = [
        "choose your language",
        "оберіть мову",
        "выберите язык",
    ]
    if not any(marker in lowered for marker in choose_language_markers):
        await profile(callback, db)
        return

    await callback.message.delete()

    user_name = callback.from_user.first_name or "друже"
    welcome_text = get_text(lang, "welcome_text").format(name=user_name)
    img_welcome = "https://i.postimg.cc/7hWHVtr6/Gemini_Generated_Image_y1ell9y1ell9y1el_(1).png"

    try:
            await callback.message.answer_photo(
                photo=img_welcome,
                caption=welcome_text,
                reply_markup=main_menu_kb(lang),
                parse_mode="HTML",
            )
            await log_chat_message(db, callback.from_user.id, "bot", welcome_text)
    except Exception as exc:
        logging.error("Welcome image send failed: %s", exc)
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
            [InlineKeyboardButton(text=_localized(_LANGUAGE_BUTTON, lang), callback_data=CB_CHANGE_LANGUAGE)],
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


@router.callback_query(F.data == CB_CHANGE_LANGUAGE)
async def change_language_from_profile(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user or not callback.message:
        return

    user_id = str(callback.from_user.id)
    doc = db.collection("users").document(user_id).get()
    user_data = doc.to_dict() or {}
    lang = user_data.get("language", "uk")

    await callback.message.edit_text(
        _localized(_LANGUAGE_PROMPT, lang),
        reply_markup=language_selection_kb(prefix=LANG_PROFILE_PREFIX),
        parse_mode="HTML",
    )
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
        await callback.answer(_localized(_USERNAME_MISSING, lang), show_alert=True)
        return

    link = f"https://t.me/{me.username}?start=ref_{callback.from_user.id}"
    share_text = _localized(_REFERRAL_SHARE_TEXT, lang).format(link=link)
    share_prompt = _localized(_REFERRAL_SHARE_PROMPT, lang)
    text = _localized(_REFERRAL_SCREEN, lang).format(
        bonus=REFERRAL_DAILY_BONUS,
        link=link,
        share_text=share_text,
    )
    share_url = "https://t.me/share/url?" + urlencode({"url": link, "text": share_prompt})

    invite_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_localized(_SEND_INVITE_BUTTON, lang), url=share_url)],
            [InlineKeyboardButton(text=get_text(lang, "btn_back_profile"), callback_data=CB_PROFILE)],
        ]
    )

    await callback.message.edit_text(text, reply_markup=invite_kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == CB_BACK_MENU)
async def back_to_menu_handler(callback: CallbackQuery, db: firestore.Client, state: FSMContext) -> None:
    if not callback.from_user:
        return

    user_id = str(callback.from_user.id)
    doc = db.collection("users").document(user_id).get()
    lang = doc.to_dict().get("language", "uk") if doc.exists else "uk"

    await release_ai_action_lock(db, callback.from_user.id)
    await state.clear()

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

    await _render_horoscope_settings(callback, db)
    await callback.answer()


@router.callback_query(F.data == CB_TOGGLE_HOROSCOPE)
async def toggle_horoscope_delivery(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user:
        return

    user_id = str(callback.from_user.id)
    doc = db.collection("users").document(user_id).get()
    user_data = doc.to_dict() or {}
    lang = user_data.get("language", "uk")
    current = bool(user_data.get("horoscope_enabled", True))
    await update_horoscope_enabled(db, callback.from_user.id, not current)
    await _render_horoscope_settings(callback, db)
    await callback.answer(_horoscope_status_text(lang, not current))


@router.callback_query(F.data.startswith("set_zodiac:"))
async def process_set_zodiac(callback: CallbackQuery, db: firestore.Client) -> None:
    if not callback.from_user:
        return

    zodiac = callback.data.split(":")[1]
    await update_user_zodiac(db, callback.from_user.id, zodiac)

    user_id = str(callback.from_user.id)
    doc = db.collection("users").document(user_id).get()
    lang = doc.to_dict().get("language", "uk") if doc.exists else "uk"

    await callback.answer(get_text(lang, "zodiac_saved"))
    await _render_horoscope_settings(callback, db)




