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
        "welcome_text": "Вітаю, <b>{name}</b>. Я — Karma.\n\nЯ тут, щоб освітити твій шлях, коли стає темно. Пам'ятай: карти не вирішують за тебе, вони лише показують вірогідності.\n\nЩо турбує твою душу сьогодні?",
        
        # 👇 НОВІ РЯДКИ ДЛЯ ПРОФІЛЮ ТА МЕНЮ 👇
        "main_menu_title": "Головне меню:",
        "btn_setup_horoscope": "🔮 Налаштувати гороскоп",
        "profile_text": "<b>🧘 Твій енергетичний баланс:</b>\n✨ Доступно зірок: <b>{balance} ⭐️</b>\n\n🔮 <b>Твій знак Зодіаку:</b> {zodiac}\n\n<b>Як поповнити запаси?</b>\nУ Всесвіті діє закон обміну. Просто обери будь-який платний розклад...\n\n<i>Енергія нікуди не зникає, вона лише змінює форму.</i>"
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
        "welcome_text": "Welcome, <b>{name}</b>. I am Karma.\n\nI am here to illuminate your path when it gets dark. Remember: cards don't make decisions for you, they only show probabilities.\n\nWhat troubles your soul today?",
        
        # 👇 НОВІ РЯДКИ ДЛЯ ПРОФІЛЮ ТА МЕНЮ 👇
        "main_menu_title": "Main Menu:",
        "btn_setup_horoscope": "🔮 Setup Horoscope",
        "profile_text": "<b>🧘 Your Energy Balance:</b>\n✨ Available stars: <b>{balance} ⭐️</b>\n\n🔮 <b>Your Zodiac sign:</b> {zodiac}\n\n<b>How to replenish?</b>\nThe Universe operates on the law of exchange. Just choose any paid reading...\n\n<i>Energy never disappears, it only changes form.</i>"
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
        "welcome_text": "Приветствую, <b>{name}</b>. Я — Karma.\n\nЯ здесь, чтобы осветить твой путь, когда становится темно. Помни: карты не решают за тебя, они лишь показывают вероятности.\n\nЧто тревожит твою душу сегодня?",
        
        # 👇 НОВІ РЯДКИ ДЛЯ ПРОФІЛЮ ТА МЕНЮ 👇
        "main_menu_title": "Главное меню:",
        "btn_setup_horoscope": "🔮 Настроить гороскоп",
        "profile_text": "<b>🧘 Твой энергетический баланс:</b>\n✨ Доступно звезд: <b>{balance} ⭐️</b>\n\n🔮 <b>Твой знак Зодиака:</b> {zodiac}\n\n<b>Как пополнить запасы?</b>\nВо Вселенной действует закон обмена. Просто выбери любой платный расклад...\n\n<i>Энергия никуда не исчезает, она лишь меняет форму.</i>"
    }
}

def get_text(lang: str, key: str) -> str:
    return LEXICON.get(lang, LEXICON["uk"]).get(key, LEXICON["uk"].get(key, key))