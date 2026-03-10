import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional

import firebase_admin
from firebase_admin import credentials, firestore


class InsufficientBalanceError(Exception):
    pass


@dataclass(frozen=True)
class UserDoc:
    user_id: int
    username: str
    first_name: str
    balance: int


_db: Optional[firestore.Client] = None


def _init_firestore_sync(firebase_cred_path: str) -> firestore.Client:
    global _db
    if _db is not None:
        return _db

    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_cred_path)
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    return _db


async def init_firestore(firebase_cred_path: str) -> firestore.Client:
    return await asyncio.to_thread(_init_firestore_sync, firebase_cred_path)


def _users_col(db: firestore.Client):
    return db.collection("users")


async def ensure_user(
    db: firestore.Client,
    *,
    user_id: int,
    username: str = "",
    first_name: str = "",
) -> None:
    def _ensure_sync() -> None:
        ref = _users_col(db).document(str(user_id))
        snap = ref.get()
        if not snap.exists:
            ref.set(
                {
                    "username": username or "",
                    "first_name": first_name or "",
                    "balance": 0,
                    "joined_at": firestore.SERVER_TIMESTAMP,
                }
            )
        else:
            updates: Dict[str, Any] = {}
            data = snap.to_dict() or {}
            if username and data.get("username") != username:
                updates["username"] = username
            if first_name and data.get("first_name") != first_name:
                updates["first_name"] = first_name
            if updates:
                ref.update(updates)

    await asyncio.to_thread(_ensure_sync)


async def get_user(db: firestore.Client, user_id: int) -> Optional[Dict[str, Any]]:
    def _get_sync() -> Optional[Dict[str, Any]]:
        ref = _users_col(db).document(str(user_id))
        snap = ref.get()
        if not snap.exists:
            return None
        return snap.to_dict() or {}

    return await asyncio.to_thread(_get_sync)


async def get_balance(db: firestore.Client, user_id: int) -> int:
    user = await get_user(db, user_id)
    if not user:
        return 0
    try:
        return int(user.get("balance", 0))
    except (TypeError, ValueError):
        return 0


async def increment_balance(db: firestore.Client, user_id: int, delta: int) -> int:
    def _tx_sync() -> int:
        ref = _users_col(db).document(str(user_id))

        @firestore.transactional
        def _run(transaction: firestore.Transaction) -> int:
            snap = ref.get(transaction=transaction)
            if not snap.exists:
                current = 0
                transaction.set(
                    ref,
                    {
                        "username": "",
                        "first_name": "",
                        "balance": 0,
                        "joined_at": firestore.SERVER_TIMESTAMP,
                    },
                )
            else:
                data = snap.to_dict() or {}
                try:
                    current = int(data.get("balance", 0))
                except (TypeError, ValueError):
                    current = 0

            new_balance = current + delta
            if new_balance < 0:
                raise InsufficientBalanceError("Not enough balance")

            transaction.update(ref, {"balance": new_balance})
            return new_balance

        transaction = db.transaction()
        return _run(transaction)

    return await asyncio.to_thread(_tx_sync)


async def set_balance(db: firestore.Client, user_id: int, balance: int) -> int:
    def _set_sync() -> int:
        ref = _users_col(db).document(str(user_id))
        snap = ref.get()
        if not snap.exists:
            ref.set(
                {
                    "username": "",
                    "first_name": "",
                    "balance": balance,
                    "joined_at": firestore.SERVER_TIMESTAMP,
                }
            )
        else:
            ref.set({"balance": balance}, merge=True)
        return balance

    return await asyncio.to_thread(_set_sync)


async def get_user_stats(db: firestore.Client) -> Dict[str, int]:
    def _stats_sync() -> Dict[str, int]:
        stats = {
            "total_users": 0,
            "users_with_balance": 0,
            "users_with_daily_card": 0,
            "users_with_zodiac": 0,
            "lang_uk": 0,
            "lang_en": 0,
            "lang_ru": 0,
        }

        for snap in _users_col(db).stream():
            data = snap.to_dict() or {}
            stats["total_users"] += 1

            try:
                balance = int(data.get("balance", 0))
            except (TypeError, ValueError):
                balance = 0
            if balance > 0:
                stats["users_with_balance"] += 1

            if data.get("last_daily_card_date"):
                stats["users_with_daily_card"] += 1

            zodiac = data.get("zodiac_sign", "all")
            if zodiac and zodiac != "all":
                stats["users_with_zodiac"] += 1

            lang = data.get("language", "uk")
            if lang == "en":
                stats["lang_en"] += 1
            elif lang == "ru":
                stats["lang_ru"] += 1
            else:
                stats["lang_uk"] += 1

        return stats

    return await asyncio.to_thread(_stats_sync)


async def update_user_zodiac(db: firestore.Client, user_id: int, zodiac_key: str) -> None:
    def _update_sync() -> None:
        doc_ref = _users_col(db).document(str(user_id))
        doc_ref.set({"zodiac_sign": zodiac_key}, merge=True)

    await asyncio.to_thread(_update_sync)


async def update_user_language(db: firestore.Client, user_id: int, lang: str) -> None:
    def _update_sync() -> None:
        doc_ref = _users_col(db).document(str(user_id))
        doc_ref.set({"language": lang}, merge=True)

    await asyncio.to_thread(_update_sync)


async def get_user_language(db: firestore.Client, user_id: int) -> str:
    def _get_sync() -> str:
        doc = _users_col(db).document(str(user_id)).get()
        if doc.exists:
            return doc.to_dict().get("language", "uk")
        return "uk"

    return await asyncio.to_thread(_get_sync)