import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    gemini_api_key: str
    firebase_cred_path: str


def load_settings() -> Settings:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    firebase_cred_path = os.getenv("FIREBASE_CRED_PATH", "").strip()

    missing = [
        name
        for name, value in (
            ("BOT_TOKEN", bot_token),
            ("GEMINI_API_KEY", gemini_api_key),
            ("FIREBASE_CRED_PATH", firebase_cred_path),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    return Settings(
        bot_token=bot_token,
        gemini_api_key=gemini_api_key,
        firebase_cred_path=firebase_cred_path,
    )
