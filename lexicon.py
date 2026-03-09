# lexicon.py

LEXICON = {
    "uk": {
        "menu_daily": "✨ Карта дня (Безкоштовно)",
        "menu_love": "❤️ Любов та Стосунки (75 ⭐️)",
        "menu_career": "💰 Гроші та Реалізація (100 ⭐️)",
        "menu_advice": "🧘 Порада Всесвіту (25 ⭐️)",
        "menu_profile": "👤 Моя карма (баланс)",
        "btn_back": "🔙 Назад в меню",
        "choose_language": "🇺🇦 Оберіть мову:\n🇬🇧 Choose your language:\n🇷🇺 Выберите язык:",
        "lang_saved": "✅ Мову збережено!",
        "welcome_text": "Вітаю, <b>{name}</b>. Я — Karma.\n\nЯ тут, щоб освітити твій шлях, коли стає темно. Пам\'ятай: карти не вирішують за тебе, вони лише показують вірогідності.\n\nЩо турбує твою душу сьогодні?",
        "main_menu_title": "Головне меню:",
        "btn_setup_horoscope": "🔮 Налаштувати гороскоп",
        "profile_text": "<b>🧘 Твій енергетичний баланс:</b>\n✨ Доступно зірок: <b>{balance} ⭐️</b>\n\n🔮 <b>Твій знак Зодіаку:</b> {zodiac}\n\n<b>Як поповнити запаси?</b>\nУ Всесвіті діє закон обміну. Просто обери будь-який платний розклад...\n\n<i>Енергія нікуди не зникає, вона лише змінює форму.</i>",
        "loading_advice": "🌌 <i>Звертаюсь до потоку...</i>",
        "loading_tarot": "🎴 <i>Тасую карти... Звертаюсь до потоків долі...</i>",
        "not_enough_stars": "❌ <b>Недостатньо зірок!</b>\nПотрібно: {cost} ⭐️\nУ тебе: {balance} ⭐️",
        "error_generate": "Вибач, енергетичні потоки зараз нестабільні. Спробуй ще раз пізніше.",
        "more_action_btn": "💫 Відчуваєш, що це не все? Обери наступну дію 👇",
        "invoice_advice_title": "Порада Всесвіту 🧘",
        "invoice_advice_desc": "Коротка мудрість або відповідь на чітке запитання.",
        "error_payment": "Недостатньо ⭐ для оплати.",
        "ask_question": "Напишіть своє запитання Всесвіту (або відправте \'...\', щоб отримати загальну пораду):",
        "default_advice_request": "Загальна порада",
        "refund_note": "Твої <b>{price} ⭐️ автоматично повернуто</b>.",
        "universe_silent": "Вибач, Всесвіт зараз мовчить.",
        "universe_answer": "✨ <i>Відповідь Всесвіту:</i>",
        "daily_already_opened": "Твоя карта на сьогодні вже відкрита!",
        "loading_daily_1": "🔮 <i>Запитую карту дня...</i>",
        "loading_daily_2": "🧘 <i>Налаштовуюся на твої вібрації...</i>",
        "loading_daily_3": "🎴 <i>Тасую колоду...</i>",
        "daily_energy_here": "✨ <i>Енергія дня вже тут...</i>",
        "invoice_love_title": "Любов та Стосунки ❤️",
        "invoice_love_desc": "Аналіз почуттів, думок партнера та майбутнього.",
        "invoice_career_title": "Гроші та Реалізація 💰",
        "invoice_career_desc": "Аналіз фінансів, кар\'єрного росту та проектів.",
        "ask_love_context": "Зосередься на людині. Напиши її ім\'я та коротко опиши, що відбувається між вами зараз.",
        "ask_career_context": "Опиши свою робочу ситуацію або проект, який тебе турбує.",
        "ask_general_context": "Опиши свою ситуацію (текстом або голосом)...",
        "loading_cards": "🔮 <i>Розкладаю карти...</i>",
        "loading_love_cards": "<i>Karma розкладає карти на: Ваші почуття, Приховані думки, Майбутнє...</i>",
        "cards_on_table": "✨ <i>Карти лягли на стіл...</i>",
        "magic_interrupted": "🌪 <i>Магічний ефір раптово перервався... Карти не захотіли говорити.</i>\n\nНе хвилюйся. {refund_note} Спробуй запитати ще раз за кілька хвилин.",
        "refund_note_balance": "Твої <b>{price} ⭐️ автоматично повернуто</b> на баланс.",
        "magic_wait": "🧘 Зачекай... Магія не терпить поспіху.",
        "zodiac_setup_title": "🔮 <b>Обери свій знак Зодіаку:</b>\n\nЯкщо обереш конкретний знак, я надсилатиму гороскоп тільки для нього. Якщо обереш «Усі знаки» — отримуватимеш повний список, щоб ділитися з друзями!",
        "btn_all_signs": "🌌 Надсилати усі знаки",
        "btn_back_profile": "🔙 Назад до профілю",
        "zodiac_saved": "✅ Знак збережено!",
        "zodiacs": {
            "aries": "♈ Овен⠀⠀⠀", "taurus": "♉ Телець⠀", "gemini": "♊ Близн.⠀",
            "cancer": "♋ Рак⠀⠀⠀⠀", "leo": "♌ Лев⠀⠀⠀⠀", "virgo": "♍ Діва⠀⠀⠀",
            "libra": "♎ Терези⠀", "scorpio": "♏ Скорп.⠀", "sagittarius": "♐ Стріл.⠀",
            "capricorn": "♑ Козеріг", "aquarius": "♒ Водолій", "pisces": "♓ Риби⠀⠀⠀",
            "all": "🌌 Усі знаки"
        },
        "karma_system_prompt": """
Role: You are Karma, a mystical tarot reader and guide. 
Tone: Empathic, mysterious, deep, using 'You' (Ty). 
Language: Ukrainian. Never say you are an AI. 

Структура твоєї відповіді має бути точно такою (ОБОВ'ЯЗКОВО роби порожній рядок між заголовком та текстом під ним, а також між самими блоками):

🎴 <b>Карти:</b>

[Назви карт та їх короткий опис]

👁 <b>Твій розклад:</b>

[Детальне тлумачення]

✨ <b>Порада від Karma:</b>

[Текст поради]

🌌 <b>Афірмація:</b>

[Текст афірмації]

ВАЖЛИВО ЩОДО ФОРМАТУВАННЯ:
Ти відправляєш повідомлення в Telegram-бот, який підтримує ТІЛЬКИ HTML-розмітку. 
СУВОРО ЗАБОРОНЕНО використовувати Markdown (ніяких зірочок ** для жирного шрифту).
Для виділення тексту використовуй ВИКЛЮЧНО HTML-теги: <b>жирний текст</b>, <i>курсив</i>.
""",
        "universe_advice_system_prompt": """
Role: Oracle. Do not use Tarot cards here. 
Give metaphorical answers using nature symbols. 
Language: Ukrainian.

Структура твоєї відповіді має бути точно такою (ОБОВ'ЯЗКОВО роби порожній рядок між заголовком та текстом під ним, а також між самими блоками):

🌌 <b>Символ:</b>

[Опис символу]

🗝 <b>Мудрість:</b>

[Текст мудрості]

⚡️ <b>Дія:</b>

[Текст дії]

ВАЖЛИВО ЩОДО ФОРМАТУВАННЯ:
Ти відправляєш повідомлення в Telegram-бот, який підтримує ТІЛЬКИ HTML-розмітку. 
СУВОРО ЗАБОРОНЕНО використовувати Markdown (ніяких зірочок ** для жирного шрифту).
Для виділення тексту використовуй ВИКЛЮЧНО HTML-теги: <b>жирний текст</b>, <i>курсив</i>.
"""
    },
    "en": {
        "menu_daily": "✨ Card of the Day (Free)",
        "menu_love": "❤️ Love & Relationships (75 ⭐️)",
        "menu_career": "💰 Career & Finances (100 ⭐️)",
        "menu_advice": "🧘 Universe Advice (25 ⭐️)",
        "menu_profile": "👤 My Karma (Balance)",
        "btn_back": "🔙 Back to Menu",
        "lang_saved": "✅ Language saved!",
        "welcome_text": "Welcome, <b>{name}</b>. I am Karma.\n\nI am here to illuminate your path when it gets dark. Remember: cards don't make decisions for you, they only show probabilities.\n\nWhat troubles your soul today?",
        "main_menu_title": "Main Menu:",
        "btn_setup_horoscope": "🔮 Setup Horoscope",
        "profile_text": "<b>🧘 Your Energy Balance:</b>\n✨ Available stars: <b>{balance} ⭐️</b>\n\n🔮 <b>Your Zodiac sign:</b> {zodiac}\n\n<b>How to replenish?</b>\nThe Universe operates on the law of exchange. Just choose any paid reading...\n\n<i>Energy never disappears, it only changes form.</i>",
        "loading_advice": "🌌 <i>Consulting the stream...</i>",
        "loading_tarot": "🎴 <i>Shuffling cards... Connecting to the flows of fate...</i>",
        "not_enough_stars": "❌ <b>Not enough stars!</b>\nNeeded: {cost} ⭐️\nYou have: {balance} ⭐️",
        "error_generate": "Sorry, energy flows are unstable right now. Try again later.",
        "more_action_btn": "💫 Feel like this isn't everything? Choose your next action 👇",
        "invoice_advice_title": "Universe Advice 🧘",
        "invoice_advice_desc": "Short wisdom or an answer to a specific question.",
        "error_payment": "Not enough ⭐ to pay.",
        "ask_question": "Write your question to the Universe (or send \'...\' to get a general advice):",
        "default_advice_request": "General advice",
        "refund_note": "Your <b>{price} ⭐️ have been automatically refunded</b>.",
        "universe_silent": "Sorry, the Universe is silent right now.",
        "universe_answer": "✨ <i>Universe's Answer:</i>",
        "daily_already_opened": "Your card for today is already open!",
        "loading_daily_1": "🔮 <i>Asking for the card of the day...</i>",
        "loading_daily_2": "🧘 <i>Tuning into your vibrations...</i>",
        "loading_daily_3": "🎴 <i>Shuffling the deck...</i>",
        "daily_energy_here": "✨ <i>The energy of the day is here...</i>",
        "invoice_love_title": "Love & Relationships ❤️",
        "invoice_love_desc": "Analysis of feelings, partner's thoughts, and future.",
        "invoice_career_title": "Career & Finances 💰",
        "invoice_career_desc": "Analysis of finances, career growth, and projects.",
        "ask_love_context": "Focus on the person. Write their name and briefly describe what is happening between you right now.",
        "ask_career_context": "Describe your work situation or project that concerns you.",
        "ask_general_context": "Describe your situation (by text or voice)...",
        "loading_cards": "🔮 <i>Laying out the cards...</i>",
        "loading_love_cards": "<i>Karma is laying out the cards for: Your feelings, Hidden thoughts, Future...</i>",
        "cards_on_table": "✨ <i>The cards are on the table...</i>",
        "magic_interrupted": "🌪 <i>The magical ether was suddenly interrupted... The cards refused to speak.</i>\n\nDon't worry. {refund_note} Try asking again in a few minutes.",
        "refund_note_balance": "Your <b>{price} ⭐️ have been automatically refunded</b> to your balance.",
        "magic_wait": "🧘 Wait... Magic doesn't tolerate haste.",
        "zodiac_setup_title": "🔮 <b>Choose your Zodiac sign:</b>\n\nIf you select a specific sign, I will send the horoscope only for it. If you choose \'All signs\', you will receive the full list to share with friends!",
        "btn_all_signs": "🌌 Send all signs",
        "btn_back_profile": "🔙 Back to Profile",
        "zodiac_saved": "✅ Sign saved!",
        "zodiacs": {
            "aries": "♈ Aries⠀⠀", "taurus": "♉ Taurus⠀", "gemini": "♊ Gemini⠀",
            "cancer": "♋ Cancer⠀", "leo": "♌ Leo⠀⠀⠀", "virgo": "♍ Virgo⠀⠀",
            "libra": "♎ Libra⠀⠀", "scorpio": "♏ Scorpio", "sagittarius": "♐ Sagitt.⠀",
            "capricorn": "♑ Capric.", "aquarius": "♒ Aquarius", "pisces": "♓ Pisces⠀",
            "all": "🌌 All signs"
        },
        "karma_system_prompt": """
Role: You are Karma, a mystical tarot reader and guide. 
Tone: Empathic, mysterious, deep, using 'You'. 
Language: English. Never say you are an AI. 

Your response structure must be exactly like this (MANDATORY: leave a blank line between the header and the text below it, and also between the blocks themselves):

🎴 <b>Cards:</b>

[Card names and their brief description]

👁 <b>Your Reading:</b>

[Detailed interpretation]

✨ <b>Advice from Karma:</b>

[Advice text]

🌌 <b>Affirmation:</b>

[Affirmation text]

IMPORTANT REGARDING FORMATTING:
You are sending a message to a Telegram bot that ONLY supports HTML markup. 
It is STRICTLY FORBIDDEN to use Markdown (no asterisks ** for bold text).
Use ONLY HTML tags to highlight text: <b>bold text</b>, <i>italic text</i>.
""",
        "universe_advice_system_prompt": """
Role: Oracle. Do not use Tarot cards here. 
Give metaphorical answers using nature symbols. 
Language: English.

Your response structure must be exactly like this (MANDATORY: leave a blank line between the header and the text below it, and also between the blocks themselves):

🌌 <b>Symbol:</b>

[Symbol description]

🗝 <b>Wisdom:</b>

[Wisdom text]

⚡️ <b>Action:</b>

[Action text]

IMPORTANT REGARDING FORMATTING:
You are sending a message to a Telegram bot that ONLY supports HTML markup. 
It is STRICTLY FORBIDDEN to use Markdown (no asterisks ** for bold text).
Use ONLY HTML tags to highlight text: <b>bold text</b>, <i>italic text</i>.
"""
    },
    "ru": {
        "menu_daily": "✨ Карта дня (Бесплатно)",
        "menu_love": "❤️ Любовь и Отношения (75 ⭐️)",
        "menu_career": "💰 Деньги и Реализация (100 ⭐️)",
        "menu_advice": "🧘 Совет Вселенной (25 ⭐️)",
        "menu_profile": "👤 Моя карма (баланс)",
        "btn_back": "🔙 Назад в меню",
        "lang_saved": "✅ Язык сохранен!",
        "welcome_text": "Приветствую, <b>{name}</b>. Я — Karma.\n\nЯ здесь, чтобы осветить твой путь, когда становится темно. Помни: карты не решают за тебя, они лишь показывают вероятности.\n\nЧто тревожит твою душу сегодня?",
        "main_menu_title": "Главное меню:",
        "btn_setup_horoscope": "🔮 Настроить гороскоп",
        "profile_text": "<b>🧘 Твой энергетический баланс:</b>\n✨ Доступно звезд: <b>{balance} ⭐️</b>\n\n🔮 <b>Твой знак Зодиака:</b> {zodiac}\n\n<b>Как пополнить запасы?</b>\nВо Вселенной действует закон обмена. Просто выбери любой платный расклад...\n\n<i>Энергия никуда не исчезает, она лишь меняет форму.</i>",
        "loading_advice": "🌌 <i>Обращаюсь к потоку...</i>",
        "loading_tarot": "🎴 <i>Карты тасуются... Обращаюсь к потокам судьбы...</i>",
        "not_enough_stars": "❌ <b>Недостаточно звезд!</b>\nНужно: {cost} ⭐️\nУ тебя: {balance} ⭐️",
        "error_generate": "Извини, энергетические потоки сейчас нестабильны. Попробуй позже.",
        "more_action_btn": "💫 Чувствуешь, что это не всё? Выбери следующее действие 👇",
        "invoice_advice_title": "Совет Вселенной 🧘",
        "invoice_advice_desc": "Короткая мудрость или ответ на четкий вопрос.",
        "error_payment": "Недостаточно ⭐ для оплаты.",
        "ask_question": "Напишите свой вопрос Вселенной (или отправьте \'...\', чтобы получить общий совет):",
        "default_advice_request": "Общий совет",
        "refund_note": "Твои <b>{price} ⭐️ автоматически возвращены</b>.",
        "universe_silent": "Извини, Вселенная сейчас молчит.",
        "universe_answer": "✨ <i>Ответ Вселенной:</i>",
        "daily_already_opened": "Твоя карта на сегодня уже открыта!",
        "loading_daily_1": "🔮 <i>Спрашиваю карту дня...</i>",
        "loading_daily_2": "🧘 <i>Настраиваюсь на твои вибрации...</i>",
        "loading_daily_3": "🎴 <i>Тасую колоду...</i>",
        "daily_energy_here": "✨ <i>Энергия дня уже здесь...</i>",
        "invoice_love_title": "Любовь и Отношения ❤️",
        "invoice_love_desc": "Анализ чувств, мыслей партнера и будущего.",
        "invoice_career_title": "Деньги и Реализация 💰",
        "invoice_career_desc": "Анализ финансов, карьерного роста и проектов.",
        "ask_love_context": "Сосредоточься на человеке. Напиши его имя и кратко опиши, что происходит между вами сейчас.",
        "ask_career_context": "Опиши свою рабочую ситуацию или проект, который тебя беспокоит.",
        "ask_general_context": "Опиши свою ситуацию (текстом или голосом)...",
        "loading_cards": "🔮 <i>Раскладываю карты...</i>",
        "loading_love_cards": "<i>Karma раскладывает карты на: Ваши чувства, Скрытые мысли, Будущее...</i>",
        "cards_on_table": "✨ <i>Карты легли на стол...</i>",
        "magic_interrupted": "🌪 <i>Магический эфир внезапно прервался... Карты не захотели говорить.</i>\n\nНе волнуйся. {refund_note} Попробуй спросить еще раз через несколько минут.",
        "refund_note_balance": "Твои <b>{price} ⭐️ автоматически возвращены</b> на баланс.",
        "magic_wait": "🧘 Подожди... Магия не терпит спешки.",
        "zodiac_setup_title": "🔮 <b>Выбери свой знак Зодиака:</b>\n\nЕсли выберешь конкретный знак, я буду присылать гороскоп только для него. Если выберешь «Все знаки» — будешь получать полный список, чтобы делиться с друзьями!",
        "btn_all_signs": "🌌 Присылать все знаки",
        "btn_back_profile": "🔙 Назад в профиль",
        "zodiac_saved": "✅ Знак сохранен!",
        "zodiacs": {
            "aries": "♈ Овен⠀⠀⠀", "taurus": "♉ Телец⠀⠀", "gemini": "♊ Близнецы",
            "cancer": "♋ Рак⠀⠀⠀⠀", "leo": "♌ Лев⠀⠀⠀⠀", "virgo": "♍ Дева⠀⠀⠀",
            "libra": "♎ Весы⠀⠀⠀", "scorpio": "♏ Скорпион", "sagittarius": "♐ Стрелец",
            "capricorn": "♑ Козерог", "aquarius": "♒ Водолей", "pisces": "♓ Рыбы⠀⠀⠀",
            "all": "🌌 Все знаки"
        },
        "karma_system_prompt": """
Role: Вы - Карма, мистический таролог и проводник.
Tone: Сопереживающий, загадочный, глубокий, используя 'Ты'.
Language: Русский. Никогда не говори, что ты ИИ.

Структура твоего ответа должна быть точно такой (ОБЯЗАТЕЛЬНО делай пустую строку между заголовком и текстом под ним, а также между самими блоками):

🎴 <b>Карты:</b>

[Названия карт и их краткое описание]

👁 <b>Твой расклад:</b>

[Подробное толкование]

✨ <b>Совет от Karma:</b>

[Текст совета]

🌌 <b>Аффирмация:</b>

[Текст аффирмации]

ВАЖНО ПО ФОРМАТИРОВАНИЮ:
Ты отправляешь сообщение в Telegram-бот, который поддерживает ТОЛЬКО HTML-разметку.
СТРОГО ЗАПРЕЩЕНО использовать Markdown (никаких звёздочек ** для жирного шрифта).
Для выделения текста используй ИСКЛЮЧИТЕЛЬНО HTML-теги: <b>жирный текст</b>, <i>курсив</i>.
""",
        "universe_advice_system_prompt": """
Role: Оракул. Не используй здесь карты Таро.
Давай метафорические ответы, используя символы природы.
Language: Русский.

Структура твоего ответа должна быть точно такой (ОБЯЗАТЕЛЬНО делай пустую строку между заголовком и текстом под ним, а также между самими блоками):

🌌 <b>Символ:</b>

[Описание символа]

🗝 <b>Мудрость:</b>

[Текст мудрости]

⚡️ <b>Действие:</b>

[Текст действия]

ВАЖНО ПО ФОРМАТИРОВАНИЮ:
Ты отправляешь сообщение в Telegram-бот, который поддерживает ТОЛЬКО HTML-разметку.
СТРОГО ЗАПРЕЩЕНО использовать Markdown (никаких звёздочек ** для жирного шрифта).
Для выделения текста используй ИСКЛЮЧИТЕЛЬНО HTML-теги: <b>жирный текст</b>, <i>курсив</i>.
"""
    }
}

def get_text(lang: str, key: str) -> str:
    """
    Retrieves a text string from the LEXICON dictionary for the given language and key.
    Falls back to Ukrainian if the specified language or key is not found.
    """
    # Fallback to 'uk' if the language is not found
    lang_lexicon = LEXICON.get(lang, LEXICON.get("uk", {}))
    
    # Get the text for the key, falling back to the 'uk' version of the key if not found
    text = lang_lexicon.get(key)
    if text is None:
        # If the key is not in the current language lexicon, try getting it from the 'uk' lexicon
        uk_lexicon = LEXICON.get("uk", {})
        text = uk_lexicon.get(key, key) # As a last resort, return the key itself
        
    return text

