import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import firebase_admin
from firebase_admin import credentials, firestore

REFERRAL_DAILY_BONUS = 1


class InsufficientBalanceError(Exception):
    pass


@dataclass(frozen=True)
class UserDoc:
    user_id: int
    username: str
    first_name: str
    balance: int


_db: Optional[firestore.Client] = None
_credential_source = ""
_credential_project_id = ""
_credential_client_email = ""

logger = logging.getLogger(__name__)


def _credential_from_json(raw_json: str) -> tuple[credentials.Certificate, dict[str, Any]]:
    try:
        service_account_info = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid FIREBASE_CREDENTIALS_JSON: expected service account JSON") from exc

    if not isinstance(service_account_info, dict):
        raise RuntimeError("Invalid FIREBASE_CREDENTIALS_JSON: expected JSON object")

    return credentials.Certificate(service_account_info), service_account_info


def _credential_from_b64(raw_b64: str) -> tuple[credentials.Certificate, dict[str, Any]]:
    stripped = raw_b64.strip()
    if stripped.startswith("{"):
        logger.warning(
            "FIREBASE_CREDENTIALS_B64 contains raw JSON, not base64; accepting it as service account JSON"
        )
        return _credential_from_json(stripped)

    normalized = "".join(stripped.split())
    try:
        decoded = base64.b64decode(normalized, validate=True).decode("utf-8")
    except Exception as exc:
        raise RuntimeError(
            "Invalid FIREBASE_CREDENTIALS_B64: expected base64-encoded service account JSON "
            f"(received {len(stripped)} characters; a real key is usually thousands of characters)"
        ) from exc

    return _credential_from_json(decoded)


def _init_firestore_sync(
    firebase_cred_path: str = "",
    *,
    firebase_credentials_json: str = "",
    firebase_credentials_b64: str = "",
) -> firestore.Client:
    global _db, _credential_source, _credential_project_id, _credential_client_email
    if _db is not None:
        return _db

    if not firebase_admin._apps:
        service_account_info: dict[str, Any] = {}
        if firebase_credentials_json:
            cred, service_account_info = _credential_from_json(firebase_credentials_json)
            _credential_source = "FIREBASE_CREDENTIALS_JSON"
        elif firebase_credentials_b64:
            cred, service_account_info = _credential_from_b64(firebase_credentials_b64)
            _credential_source = "FIREBASE_CREDENTIALS_B64"
        elif firebase_cred_path:
            cred = credentials.Certificate(firebase_cred_path)
            _credential_source = "FIREBASE_CRED_PATH"
            try:
                with open(firebase_cred_path, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                if isinstance(loaded, dict):
                    service_account_info = loaded
            except Exception:
                logger.warning("Could not read Firebase credential metadata from %s", firebase_cred_path)
        else:
            raise RuntimeError(
                "Firebase credentials are not configured. Set FIREBASE_CRED_PATH, "
                "FIREBASE_CREDENTIALS_JSON, or FIREBASE_CREDENTIALS_B64."
            )

        _credential_project_id = str(service_account_info.get("project_id", ""))
        _credential_client_email = str(service_account_info.get("client_email", ""))
        logger.info(
            "Initializing Firebase Admin using %s project_id=%s client_email=%s",
            _credential_source,
            _credential_project_id or "<unknown>",
            _credential_client_email or "<unknown>",
        )
        firebase_admin.initialize_app(cred)

    # Use REST transport to bypass gRPC/HTTP2 issues on Render
    import google.auth
    from google.cloud import firestore as google_firestore
    app = firebase_admin.get_app()
    app_cred = app.credential.get_credential()
    _db = google_firestore.Client(
        project=_credential_project_id or app.project_id,
        credentials=app_cred,
        transport="rest",
    )
    return _db


async def init_firestore(
    firebase_cred_path: str = "",
    *,
    firebase_credentials_json: str = "",
    firebase_credentials_b64: str = "",
) -> firestore.Client:
    return await asyncio.to_thread(
        _init_firestore_sync,
        firebase_cred_path,
        firebase_credentials_json=firebase_credentials_json,
        firebase_credentials_b64=firebase_credentials_b64,
    )


async def check_firestore_access(db: firestore.Client) -> bool:
    def _check_sync() -> list[tuple[str, bool, str]]:
        diagnostics_ref = db.collection("_diagnostics").document("firestore_access_check")
        checks: list[tuple[str, bool, str]] = []

        operations = (
            ("document_get", lambda: diagnostics_ref.get()),
            ("query_stream", lambda: list(db.collection("users").limit(1).stream())),
            (
                "document_set",
                lambda: diagnostics_ref.set(
                    {
                        "checked_at": firestore.SERVER_TIMESTAMP,
                        "source": "startup_probe",
                    },
                    merge=True,
                ),
            ),
        )

        for name, operation in operations:
            try:
                operation()
            except Exception as exc:
                checks.append((name, False, f"{type(exc).__name__}: {exc}"))
            else:
                checks.append((name, True, "ok"))

        return checks

    client_project = getattr(db, "project", "<unknown>")
    checks = await asyncio.to_thread(_check_sync)
    failed = [check for check in checks if not check[1]]

    for operation, ok, detail in checks:
        log = logger.info if ok else logger.error
        log(
            "FIRESTORE_ACCESS_CHECK operation=%s ok=%s credential_source=%s credential_project_id=%s client_project=%s client_email=%s detail=%s",
            operation,
            ok,
            _credential_source or "<unknown>",
            _credential_project_id or "<unknown>",
            client_project,
            _credential_client_email or "<unknown>",
            detail,
        )

    return not failed


def _users_col(db: firestore.Client):
    return db.collection("users")


async def ensure_user(
    db: firestore.Client,
    *,
    user_id: int,
    username: str = "",
    first_name: str = "",
) -> bool:
    def _ensure_sync() -> bool:
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
            return True
        else:
            updates: Dict[str, Any] = {}
            data = snap.to_dict() or {}
            if username and data.get("username") != username:
                updates["username"] = username
            if first_name and data.get("first_name") != first_name:
                updates["first_name"] = first_name
            if updates:
                ref.update(updates)
            return False

    return await asyncio.to_thread(_ensure_sync)


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


async def bind_referrer(db: firestore.Client, user_id: int, referrer_id: int) -> bool:
    def _tx_sync() -> bool:
        if user_id == referrer_id:
            return False

        user_ref = _users_col(db).document(str(user_id))
        referrer_ref = _users_col(db).document(str(referrer_id))

        @firestore.transactional
        def _run(transaction: firestore.Transaction) -> bool:
            user_snap = user_ref.get(transaction=transaction)
            referrer_snap = referrer_ref.get(transaction=transaction)

            if not user_snap.exists or not referrer_snap.exists:
                return False

            user_data = user_snap.to_dict() or {}
            if user_data.get("referred_by"):
                return False

            transaction.set(
                user_ref,
                {
                    "referred_by": referrer_id,
                    "referred_at": firestore.SERVER_TIMESTAMP,
                    "referral_bonus_granted": False,
                },
                merge=True,
            )
            return True

        transaction = db.transaction()
        return _run(transaction)

    return await asyncio.to_thread(_tx_sync)


async def grant_referral_bonus_for_daily_card(db: firestore.Client, user_id: int, bonus: int = REFERRAL_DAILY_BONUS) -> Optional[int]:
    def _tx_sync() -> Optional[int]:
        user_ref = _users_col(db).document(str(user_id))

        @firestore.transactional
        def _run(transaction: firestore.Transaction) -> Optional[int]:
            user_snap = user_ref.get(transaction=transaction)
            if not user_snap.exists:
                return None

            user_data = user_snap.to_dict() or {}
            referrer_id = user_data.get("referred_by")
            if not referrer_id or user_data.get("referral_bonus_granted"):
                return None

            try:
                referrer_id_int = int(referrer_id)
            except (TypeError, ValueError):
                return None

            if referrer_id_int == user_id:
                return None

            referrer_ref = _users_col(db).document(str(referrer_id_int))
            referrer_snap = referrer_ref.get(transaction=transaction)
            if not referrer_snap.exists:
                return None

            referrer_data = referrer_snap.to_dict() or {}
            try:
                current_balance = int(referrer_data.get("balance", 0))
            except (TypeError, ValueError):
                current_balance = 0
            try:
                referrals_count = int(referrer_data.get("referrals_count", 0))
            except (TypeError, ValueError):
                referrals_count = 0
            try:
                referral_rewards_total = int(referrer_data.get("referral_rewards_total", 0))
            except (TypeError, ValueError):
                referral_rewards_total = 0
            try:
                matrix_free_slots = int(referrer_data.get("matrix_free_slots", 2))
            except (TypeError, ValueError):
                matrix_free_slots = 2

            transaction.set(
                referrer_ref,
                {
                    "balance": current_balance + bonus,
                    "referrals_count": referrals_count + 1,
                    "referral_rewards_total": referral_rewards_total + bonus,
                    "matrix_free_slots": matrix_free_slots + 1,
                },
                merge=True,
            )
            transaction.set(
                user_ref,
                {
                    "referral_bonus_granted": True,
                    "referral_bonus_granted_at": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )
            return referrer_id_int

        transaction = db.transaction()
        return _run(transaction)

    return await asyncio.to_thread(_tx_sync)



async def get_referred_users(db: firestore.Client, referrer_id: int) -> list[Dict[str, Any]]:
    def _get_sync() -> list[Dict[str, Any]]:
        items: list[Dict[str, Any]] = []
        for snap in _users_col(db).where("referred_by", "==", referrer_id).stream():
            data = snap.to_dict() or {}
            data["user_id"] = int(snap.id)
            items.append(data)
        items.sort(key=lambda item: int(item.get("user_id", 0)))
        return items

    return await asyncio.to_thread(_get_sync)
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
            "users_referred": 0,
            "active_referrers": 0,
            "total_referral_rewards": 0,
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

            if data.get("referred_by"):
                stats["users_referred"] += 1

            try:
                referrals_count = int(data.get("referrals_count", 0))
            except (TypeError, ValueError):
                referrals_count = 0
            if referrals_count > 0:
                stats["active_referrers"] += 1

            try:
                referral_rewards_total = int(data.get("referral_rewards_total", 0))
            except (TypeError, ValueError):
                referral_rewards_total = 0
            stats["total_referral_rewards"] += referral_rewards_total

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

async def update_horoscope_enabled(db: firestore.Client, user_id: int, enabled: bool) -> None:
    def _update_sync() -> None:
        doc_ref = _users_col(db).document(str(user_id))
        doc_ref.set({"horoscope_enabled": enabled}, merge=True)

    await asyncio.to_thread(_update_sync)

async def claim_daily_card_slot(db: firestore.Client, user_id: int, date_key: str) -> str:
    def _tx_sync() -> str:
        ref = _users_col(db).document(str(user_id))

        @firestore.transactional
        def _run(transaction: firestore.Transaction) -> str:
            snap = ref.get(transaction=transaction)
            data = snap.to_dict() or {} if snap.exists else {}

            if data.get("last_daily_card_date") == date_key:
                return "opened"
            if data.get("daily_card_lock_date") == date_key:
                return "locked"

            transaction.set(
                ref,
                {
                    "daily_card_lock_date": date_key,
                    "daily_card_lock_at": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )
            return "claimed"

        transaction = db.transaction()
        return _run(transaction)

    return await asyncio.to_thread(_tx_sync)


async def complete_daily_card_slot(db: firestore.Client, user_id: int, date_key: str) -> None:
    def _update_sync() -> None:
        ref = _users_col(db).document(str(user_id))
        ref.set(
            {
                "last_daily_card_date": date_key,
                "daily_card_lock_date": firestore.DELETE_FIELD,
                "daily_card_lock_at": firestore.DELETE_FIELD,
            },
            merge=True,
        )

    await asyncio.to_thread(_update_sync)


async def release_daily_card_slot(db: firestore.Client, user_id: int, date_key: str) -> None:
    def _tx_sync() -> None:
        ref = _users_col(db).document(str(user_id))

        @firestore.transactional
        def _run(transaction: firestore.Transaction) -> None:
            snap = ref.get(transaction=transaction)
            data = snap.to_dict() or {} if snap.exists else {}
            if data.get("last_daily_card_date") == date_key:
                return
            if data.get("daily_card_lock_date") != date_key:
                return
            transaction.set(
                ref,
                {
                    "daily_card_lock_date": firestore.DELETE_FIELD,
                    "daily_card_lock_at": firestore.DELETE_FIELD,
                },
                merge=True,
            )

        transaction = db.transaction()
        _run(transaction)


async def log_chat_message(db: firestore.Client, user_id: int, role: str, text: str) -> None:
    def _log_sync() -> None:
        ref = _users_col(db).document(str(user_id)).collection("chat_history").document()
        ref.set(
            {
                "role": role,
                "text": text,
                "timestamp": firestore.SERVER_TIMESTAMP,
            }
        )

    await asyncio.to_thread(_log_sync)


async def get_chat_history(db: firestore.Client, user_id: int, limit: int = 20) -> list[Dict[str, Any]]:
    def _get_sync() -> list[Dict[str, Any]]:
        history: list[Dict[str, Any]] = []
        query = (
            _users_col(db)
            .document(str(user_id))
            .collection("chat_history")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        for snap in query.stream():
            data = snap.to_dict() or {}
            history.append(data)
        return history

    return await asyncio.to_thread(_get_sync)

async def claim_ai_action_lock(db: firestore.Client, user_id: int, action_key: str) -> bool:
    def _tx_sync() -> bool:
        ref = _users_col(db).document(str(user_id))

        @firestore.transactional
        def _run(transaction: firestore.Transaction) -> bool:
            snap = ref.get(transaction=transaction)
            data = snap.to_dict() or {} if snap.exists else {}
            
            if data.get("active_ai_lock"):
                lock_at = data.get("active_ai_lock_at")
                if lock_at:
                    import datetime
                    now = datetime.datetime.now(datetime.timezone.utc)
                    if (now - lock_at).total_seconds() < 300:
                        return False
            
            transaction.set(
                ref,
                {
                    "active_ai_lock": action_key,
                    "active_ai_lock_at": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )
            return True

        transaction = db.transaction()
        return _run(transaction)

    return await asyncio.to_thread(_tx_sync)


async def release_ai_action_lock(db: firestore.Client, user_id: int, action_key: str | None = None) -> None:
    def _release_sync() -> None:
        ref = _users_col(db).document(str(user_id))
        if action_key is not None:
            snap = ref.get()
            data = snap.to_dict() or {} if snap.exists else {}
            if data.get("active_ai_lock") != action_key:
                return
        ref.set(
            {
                "active_ai_lock": firestore.DELETE_FIELD,
                "active_ai_lock_at": firestore.DELETE_FIELD,
            },
            merge=True,
        )

    try:
        await asyncio.to_thread(_release_sync)
    except Exception as exc:
        logger.warning(
            "AI_ACTION_LOCK_RELEASE_FAILED user_id=%s error_type=%s error=%s",
            user_id,
            type(exc).__name__,
            exc,
        )
