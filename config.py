import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    gemini_api_key: str
    firebase_cred_path: str
    firebase_credentials_json: str
    firebase_credentials_b64: str
    primary_model_name: str
    fallback_model_name: str


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def load_settings() -> Settings:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    firebase_cred_path = _first_env("FIREBASE_CRED_PATH", "GOOGLE_APPLICATION_CREDENTIALS")
    firebase_credentials_json = _first_env(
        "FIREBASE_CREDENTIALS_JSON",
        "FIREBASE_SERVICE_ACCOUNT_JSON",
        "GOOGLE_APPLICATION_CREDENTIALS_JSON",
    )
    firebase_credentials_b64 = _first_env(
        "FIREBASE_CREDENTIALS_B64",
        "FIREBASE_SERVICE_ACCOUNT_B64",
        "GOOGLE_APPLICATION_CREDENTIALS_B64",
    )
    primary_model_name = os.getenv("PRIMARY_MODEL_NAME", "gemini-3.1-flash-lite").strip()
    fallback_model_name = os.getenv("FALLBACK_MODEL_NAME", "gemini-1.5-pro").strip()

    missing = [
        name
        for name, value in (
            ("BOT_TOKEN", bot_token),
            ("GEMINI_API_KEY", gemini_api_key),
        )
        if not value
    ]
    if not (firebase_cred_path or firebase_credentials_json or firebase_credentials_b64):
        missing.append(
            "FIREBASE_CRED_PATH or FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_B64"
        )
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    return Settings(
        bot_token=bot_token,
        gemini_api_key=gemini_api_key,
        firebase_cred_path=firebase_cred_path,
        firebase_credentials_json=firebase_credentials_json,
        firebase_credentials_b64=firebase_credentials_b64,
        primary_model_name=primary_model_name,
        fallback_model_name=fallback_model_name,
    )