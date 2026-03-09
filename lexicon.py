# lexicon.py

LEXICON = {
    "uk": {
        "menu_daily": "✨ Карта дня (Безкоштовно)",
        "menu_love": "❤️ Любов та стосунки (75⭐️)",
        "menu_career": "💰 Гроші та кар'єра (100⭐️)",
        "menu_advice": "🧘 Порада Всесвіту (25⭐️)",
        "menu_profile": "👤 Моя карма (баланс)",
        "btn_back": "🔙 Назад в меню",
        "choose_language": "🇺🇦 Оберіть мову:\n🇬🇧 Choose your language:\n🏳️ Выберите язык:",
        "lang_saved": "✅ Мову збережено!"
    },
    "en": {
        "menu_daily": "✨ Daily Card (Free)",
        "menu_love": "❤️ Love & Romance (75⭐️)",
        "menu_career": "💰 Wealth & Career (100⭐️)",
        "menu_advice": "🧘 Universe Advice (25⭐️)",
        "menu_profile": "👤 My Karma Balance",
        "btn_back": "🔙 Back to Menu",
        "choose_language": "🇺🇦 Оберіть мову:\n🇬🇧 Choose your language:\n🏳️ Выберите язык:",
        "lang_saved": "✅ Language saved!"
    },
    "ru": {
        "menu_daily": "✨ Карта дня (Бесплатно)",
        "menu_love": "❤️ Любовь и отношения (75⭐️)",
        "menu_career": "💰 Деньги и карьера (100⭐️)",
        "menu_advice": "🧘 Совет Вселенной (25⭐️)",
        "menu_profile": "👤 Моя карма (баланс)",
        "btn_back": "🔙 Назад в меню",
        "choose_language": "🇺🇦 Оберіть мову:\n🇬🇧 Choose your language:\n🏳️ Выберите язык:",
        "lang_saved": "✅ Язык сохранен!"
    }
}

def get_text(lang: str, key: str) -> str:
    """Функція для безпечного отримання перекладу. Якщо мови чи ключа немає - повертає українську."""
    return LEXICON.get(lang, LEXICON["uk"]).get(key, LEXICON["uk"].get(key, key))