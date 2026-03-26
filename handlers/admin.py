from __future__ import annotations

import os
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from firebase_admin import firestore

from firebase_db import get_chat_history, get_referred_users, get_user, get_user_stats, set_balance

router = Router()

CB_ADMIN_STATS = "admin:stats"
CB_ADMIN_USER = "admin:user"
CB_ADMIN_BACK = "admin:back"
CB_ADMIN_SET_BALANCE = "admin:set_balance"
CB_ADMIN_REFERRALS = "admin:referrals"
CB_ADMIN_HISTORY = "admin:history"

_admin_env = os.getenv("ADMIN_IDS", "469764985")
ADMIN_IDS = {int(x.strip()) for x in _admin_env.split(",") if x.strip().isdigit()}


class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_balance = State()


def _is_admin(user_id: int | None) -> bool:
    return bool(user_id and user_id in ADMIN_IDS)


def _admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Статистика", callback_data=CB_ADMIN_STATS)],
            [InlineKeyboardButton(text="Користувач", callback_data=CB_ADMIN_USER)],
        ]
    )


def _user_card_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Запрошені користувачі", callback_data=f"{CB_ADMIN_REFERRALS}:{user_id}")],
            [InlineKeyboardButton(text="Історія переписки", callback_data=f"{CB_ADMIN_HISTORY}:{user_id}")],
            [InlineKeyboardButton(text="Змінити баланс", callback_data=f"{CB_ADMIN_SET_BALANCE}:{user_id}")],
            [InlineKeyboardButton(text="Назад", callback_data=CB_ADMIN_BACK)],
        ]
    )


def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data=CB_ADMIN_BACK)]]
    )


def _user_back_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="До користувача", callback_data=f"{CB_ADMIN_REFERRALS}:{user_id}:back")]]
    )


def _format_username(username: str) -> str:
    return f"@{username}" if username else "-"


def _format_user_card(user_id: int, user_data: dict[str, Any]) -> str:
    username = user_data.get("username") or ""
    first_name = user_data.get("first_name") or "-"
    language = user_data.get("language") or "uk"
    zodiac = user_data.get("zodiac_sign") or "all"
    last_daily = user_data.get("last_daily_card_date") or "-"
    balance = int(user_data.get("balance", 0) or 0)
    referred_by = user_data.get("referred_by") or "-"
    referral_bonus_granted = "так" if user_data.get("referral_bonus_granted") else "ні"
    referrals_count = int(user_data.get("referrals_count", 0) or 0)
    referral_rewards_total = int(user_data.get("referral_rewards_total", 0) or 0)

    return (
        "<b>Користувач</b>\n\n"
        f"ID: <code>{user_id}</code>\n"
        f"Username: {_format_username(username)}\n"
        f"Ім'я: {first_name}\n"
        f"Мова: {language}\n"
        f"Знак: {zodiac}\n"
        f"Баланс: <b>{balance}</b> ⭐\n"
        f"Остання карта дня: {last_daily}\n\n"
        f"Запрошений від: <code>{referred_by}</code>\n"
        f"Реферальний бонус уже видано: {referral_bonus_granted}\n"
        f"Запрошено друзів: {referrals_count}\n"
        f"Зароблено по рефералці: <b>{referral_rewards_total}</b> ⭐"
    )


def _format_referrals_list(user_id: int, referrals: list[dict[str, Any]]) -> str:
    if not referrals:
        return (
            "<b>Запрошені користувачі</b>\n\n"
            f"Користувач <code>{user_id}</code> поки нікого не запросив."
        )

    lines = [
        "<b>Запрошені користувачі</b>",
        "",
        f"Реферер: <code>{user_id}</code>",
        f"Усього: <b>{len(referrals)}</b>",
        "",
    ]

    for idx, item in enumerate(referrals[:25], start=1):
        invited_user_id = item.get("user_id", "-")
        username = _format_username(item.get("username") or "")
        first_name = item.get("first_name") or "-"
        lang = item.get("language") or "uk"
        bonus_granted = "так" if item.get("referral_bonus_granted") else "ні"
        last_daily = item.get("last_daily_card_date") or "-"
        lines.append(
            f"{idx}. <code>{invited_user_id}</code> | {username} | {first_name} | {lang} | бонус: {bonus_granted} | карта дня: {last_daily}"
        )

    if len(referrals) > 25:
        lines.extend(["", f"Показано перші 25 із {len(referrals)}."])

    return "\n".join(lines)


async def _show_admin_home(target: Message | CallbackQuery) -> None:
    text = (
        "<b>Адмінка Karma</b>\n\n"
        "Тут можна дивитися базову статистику і керувати користувачами вручну."
    )
    if isinstance(target, CallbackQuery):
        if target.message:
            await target.message.edit_text(text, reply_markup=_admin_menu_kb(), parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(text, reply_markup=_admin_menu_kb(), parse_mode="HTML")


@router.message(Command("admin"))
async def admin_entry(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return

    await state.clear()
    await _show_admin_home(message)


@router.callback_query(F.data == CB_ADMIN_BACK)
async def admin_back(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        return

    await state.clear()
    await _show_admin_home(callback)


@router.callback_query(F.data == CB_ADMIN_STATS)
async def admin_stats(callback: CallbackQuery, db: firestore.Client) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        return

    stats = await get_user_stats(db)
    text = (
        "<b>Статистика</b>\n\n"
        f"Всього користувачів: <b>{stats['total_users']}</b>\n"
        f"З балансом > 0: <b>{stats['users_with_balance']}</b>\n"
        f"Хоч раз відкривали карту дня: <b>{stats['users_with_daily_card']}</b>\n"
        f"Обрали знак зодіаку: <b>{stats['users_with_zodiac']}</b>\n\n"
        f"Запрошені по рефералці: <b>{stats['users_referred']}</b>\n"
        f"Активні реферери: <b>{stats['active_referrers']}</b>\n"
        f"Всього видано реферальних бонусів: <b>{stats['total_referral_rewards']}</b> ⭐\n\n"
        f"Мови: uk <b>{stats['lang_uk']}</b> | en <b>{stats['lang_en']}</b> | ru <b>{stats['lang_ru']}</b>"
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=_back_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == CB_ADMIN_USER)
async def admin_user_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        return

    await state.set_state(AdminStates.waiting_for_user_id)
    if callback.message:
        await callback.message.edit_text(
            "Надішли <b>user_id</b> користувача одним повідомленням.",
            reply_markup=_back_kb(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.message(AdminStates.waiting_for_user_id)
async def admin_user_lookup(message: Message, state: FSMContext, db: firestore.Client) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return

    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Потрібен числовий user_id.", reply_markup=_back_kb())
        return

    target_user_id = int(raw)
    user_data = await get_user(db, target_user_id)
    if not user_data:
        await message.answer("Користувача не знайдено.", reply_markup=_back_kb())
        return

    await state.clear()
    await message.answer(
        _format_user_card(target_user_id, user_data),
        reply_markup=_user_card_kb(target_user_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith(f"{CB_ADMIN_REFERRALS}:"))
async def admin_referrals(callback: CallbackQuery, db: firestore.Client) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        return

    if not callback.message:
        await callback.answer()
        return

    parts = callback.data.split(":")
    target_user_id = int(parts[2 if parts[-1] == "back" else 1]) if parts[-1] == "back" else int(parts[-1])

    if parts[-1] == "back":
        user_data = await get_user(db, target_user_id)
        if not user_data:
            await callback.answer("Користувача не знайдено.", show_alert=True)
            return
        await callback.message.edit_text(
            _format_user_card(target_user_id, user_data),
            reply_markup=_user_card_kb(target_user_id),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    referrals = await get_referred_users(db, target_user_id)
    await callback.message.edit_text(
        _format_referrals_list(target_user_id, referrals),
        reply_markup=_user_back_kb(target_user_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB_ADMIN_SET_BALANCE}:"))
async def admin_set_balance_prompt(callback: CallbackQuery, state: FSMContext, db: firestore.Client) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        return

    target_user_id = int(callback.data.split(":")[-1])
    user_data = await get_user(db, target_user_id)
    if not user_data:
        await callback.answer("Користувача не знайдено.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_balance)
    await state.update_data(target_user_id=target_user_id)

    if callback.message:
        await callback.message.edit_text(
            _format_user_card(target_user_id, user_data) + "\n\nНадішли новий баланс цілим числом.",
            reply_markup=_back_kb(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.message(AdminStates.waiting_for_balance)
async def admin_set_balance_value(message: Message, state: FSMContext, db: firestore.Client) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return

    raw = (message.text or "").strip()
    if raw.startswith("+"):
        raw = raw[1:]
    if not raw.isdigit():
        await message.answer("Баланс має бути цілим невід'ємним числом.", reply_markup=_back_kb())
        return

    new_balance = int(raw)
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if not target_user_id:
        await state.clear()
        await message.answer(
            "Сесія зміни балансу втрачена. Зайди в адмінку ще раз.",
            reply_markup=_admin_menu_kb(),
        )
        return

    await set_balance(db, int(target_user_id), new_balance)
    user_data = await get_user(db, int(target_user_id)) or {}
    await state.clear()
    await message.answer(
        _format_user_card(int(target_user_id), user_data),
        reply_markup=_user_card_kb(int(target_user_id)),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith(f"{CB_ADMIN_HISTORY}:"))
async def admin_chat_history(callback: CallbackQuery, db: firestore.Client) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        return

    if not callback.message:
        await callback.answer()
        return

    parts = callback.data.split(":")
    target_user_id = int(parts[-1])

    history = await get_chat_history(db, target_user_id, limit=20)
    if not history:
        await callback.answer("Історія переписки порожня або ще не створена.", show_alert=True)
        return

    # Форматуємо історію (останні повідомлення будуть в кінці)
    history.reverse()

    lines = [f"<b>Історія переписки (останні 20)</b>\nUser ID: <code>{target_user_id}</code>\n"]
    for msg in history:
        role = "👤 Юзер" if msg["role"] == "user" else "🤖 Karma"
        raw_text = msg["text"]
        text = (raw_text[:150] + "...") if len(raw_text) > 150 else raw_text
        lines.append(f"<b>{role}:</b>\n{text}\n")

    text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=_user_back_kb(target_user_id), parse_mode="HTML")
    await callback.answer()