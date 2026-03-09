# lexicon.py

LEXICON = {
    "uk": {
        "menu_daily": "✨ Карта дня (Безкоштовно)",
        "menu_love": "❤️ Любов та Стосунки (75 ⭐️)",
        "menu_career": "💰 Гроші та Реалізація (100 ⭐️)",
        "menu_advice": "🧘 Порада Всесвіту (25 ⭐️)",
        "menu_profile": "👤 Моя карма (баланс)",
        "btn_back": "🔙 Назад в меню",
        "choose_language": "🇺🇦 Оберіть мову:\n🇬🇧 Choose your language:\n🏳️ Выберите язык:",
        "lang_saved": "✅ Мову збережено! / Language saved! / Язык сохранен!"
    },
    "en": {
        "menu_daily": "✨ Card of the Day (Free)",
        "menu_love": "❤️ Love & Relationships (75 ⭐️)",
        "menu_career": "💰 Career & Finances (100 ⭐️)",
        "menu_advice": "🧘 Universe Advice (25 ⭐️)",
        "menu_profile": "👤 My Karma (Balance)",
        "btn_back": "🔙 Back to Menu",
        "choose_language": "🇺🇦 Оберіть мову:\n🇬🇧 Choose your language:\n🏳️ Выберите язык:",
        "lang_saved": "✅ Language saved!"
    },
    "ru": {
        "menu_daily": "✨ Карта дня (Бесплатно)",
        "menu_love": "❤️ Любовь и Отношения (75 ⭐️)",
        "menu_career": "💰 Деньги и Реализация (100 ⭐️)",
        "menu_advice": "🧘 Совет Вселенной (25 ⭐️)",
        "menu_profile": "👤 Моя карма (баланс)",
        "btn_back": "🔙 Назад в меню",
        "choose_language": "🇺🇦 Оберіть мову:\n🇬🇧 Choose your language:\n🏳️ Выберите язык:",
        "lang_saved": "✅ Язык сохранен!"
    }
}

def get_text(lang: str, key: str) -> str:
    """Функція для безпечного отримання перекладу. Якщо мови чи ключа немає - повертає українську."""
    return LEXICON.get(lang, LEXICON["uk"]).get(key, LEXICON["uk"].get(key, key))