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
        "lang_saved": "✅ Мову збережено!",
        "welcome_text": "Вітаю, <b>{name}</b>. Я — Karma.\n\nЯ тут, щоб освітити твій шлях, коли стає темно. Пам'ятай: карти не вирішують за тебе, вони лише показують вірогідності.\n\nЩо турбує твою душу сьогодні?"
    },
    "en": {
        "menu_daily": "✨ Card of the Day (Free)",
        "menu_love": "❤️ Love & Relationships (75 ⭐️)",
        "menu_career": "💰 Career & Finances (100 ⭐️)",
        "menu_advice": "🧘 Universe Advice (25 ⭐️)",
        "menu_profile": "👤 My Karma (Balance)",
        "btn_back": "🔙 Back to Menu",
        "choose_language": "🇺🇦 Оберіть мову:\n🇬🇧 Choose your language:\n🏳️ Выберите язык:",
        "lang_saved": "✅ Language saved!",
        "welcome_text": "Welcome, <b>{name}</b>. I am Karma.\n\nI am here to illuminate your path when it gets dark. Remember: cards don't make decisions for you, they only show probabilities.\n\nWhat troubles your soul today?"
    },
    "ru": {
        "menu_daily": "✨ Карта дня (Бесплатно)",
        "menu_love": "❤️ Любовь и Отношения (75 ⭐️)",
        "menu_career": "💰 Деньги и Реализация (100 ⭐️)",
        "menu_advice": "🧘 Совет Вселенной (25 ⭐️)",
        "menu_profile": "👤 Моя карма (баланс)",
        "btn_back": "🔙 Назад в меню",
        "choose_language": "🇺🇦 Оберіть мову:\n🇬🇧 Choose your language:\n🏳️ Выберите язык:",
        "lang_saved": "✅ Язык сохранен!",
        "welcome_text": "Приветствую, <b>{name}</b>. Я — Karma.\n\nЯ здесь, чтобы осветить твой путь, когда становится темно. Помни: карты не решают за тебя, они лишь показывают вероятности.\n\nЧто тревожит твою душу сегодня?"
    }
}

def get_text(lang: str, key: str) -> str:
    return LEXICON.get(lang, LEXICON["uk"]).get(key, LEXICON["uk"].get(key, key))