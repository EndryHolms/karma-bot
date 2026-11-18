from pathlib import Path

from aiogram.types import FSInputFile


BRAND_ASSETS = Path(__file__).resolve().parents[1] / "assets" / "karma"


def brand_photo(name: str, lang: str | None = None) -> FSInputFile:
    if lang is None:
        return FSInputFile(BRAND_ASSETS / f"{name}.jpg")
    language = lang if lang in {"uk", "en", "ru"} else "uk"
    return FSInputFile(BRAND_ASSETS / language / f"{name}.jpg")
