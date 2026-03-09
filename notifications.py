import asyncio
import logging
import re
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from firebase_admin import firestore
from keyboards import main_menu_kb

async def send_daily_reminders(bot: Bot, db: firestore.Client):
    logging.info("Починаю розсилку нагадувань...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Отримуємо всіх користувачів з бази
    users_ref = db.collection("users").stream()
    
    count = 0
    for doc in users_ref:
        user_data = doc.to_dict()
        user_id = doc.id # ID користувача є назвою документа
        last_date = user_data.get("last_daily_card_date")
        
        # Якщо людина сьогодні ще НЕ отримувала карту
        if last_date != today_str:
            try:
                text = (
                    "✨ <i>Всесвіт має для тебе послання...</i>\n\n"
                    "Твоя Карта Дня на сьогодні ще не відкрита. "
                    "Дізнайся, які енергії тебе оточують просто зараз 👇"
                )
                await bot.send_message(
                    chat_id=user_id, 
                    text=text, 
                    reply_markup=main_menu_kb()
                )
                count += 1
                
                # ЗАХИСТ ВІД БАНУ: Telegram дозволяє не більше 30 повідомлень на секунду.
                # Робимо маленьку паузу між кожним повідомленням.
                await asyncio.sleep(0.1)
                
            except TelegramForbiddenError:
                # Цю помилку видає Telegram, якщо користувач заблокував бота.
                # Ми просто ігноруємо її і йдемо далі.
                pass
            except Exception as e:
                logging.error(f"Помилка розсилки для {user_id}: {e}")
                
    logging.info(f"Нагадування успішно надіслано {count} користувачам.")
    # Онови імпорти зверху
from keyboards import main_menu_kb, horoscope_share_menu_kb 
import asyncio
import logging
from aiogram import Bot
from firebase_admin import firestore

# ... (функція send_daily_reminders залишається без змін) ...

async def send_daily_horoscope(bot: Bot, db: firestore.Client, tarot_model):
    logging.info("Починаю генерацію та розсилку гороскопів...")
    
    prompt = (
        "Напиши іронічний, кумедний та дуже життєвий гороскоп на сьогодні для всіх 12 знаків зодіаку. "
        "Стиль: сарказм, втома від роботи, жарти про гроші, погоду та колишніх. "
        "УВАГА: СУВОРО ЗАБОРОНЕНО використовувати Markdown зірочки (**) для виділення тексту! "
        "Для жирного шрифту використовуй ТІЛЬКИ HTML-теги <b>текст</b>. "
        "Усі заголовки пиши виключно українською мовою. "
        "Обов'язково роби порожній рядок (подвійний Enter) між кожним знаком зодіаку та між блоками тексту. "
        "Структура твоєї відповіді має бути точно такою:\n\n"
        "[Твій містично-іронічний вступ]\n\n"
        "🎴 <b>Карти:</b> [назви 3 карт та їх іронічне значення]\n\n"
        "👁 <b>Твій гороскоп:</b>\n\n"
        "♈ Овен - текст...\n\n"
        "♉ Телець - текст...\n\n"
        "[...і так для всіх 12 знаків...]\n\n"
        "✨ <b>Порада від Karma:</b>\n"
        "[текст поради]\n\n"
        "🌌 <b>Афірмація:</b>\n"
        "[текст афірмації]"
    )
    
    try:
        response = await asyncio.to_thread(tarot_model.generate_content, prompt)
        raw_text = getattr(response, "text", "").strip()
    except Exception as e:
        logging.error(f"Помилка генерації гороскопу: {e}")
        return

    if not raw_text:
        return

    # === ЛОГІКА РОЗДІЛЕННЯ ТЕКСТУ ПО ЗНАКАХ ===
    
    # 1. Знаходимо вступ (до першого знака зодіаку)
    intro_match = re.split(r'♈|♉|♊|♋|♌|♍|♎|♏|♐|♑|♒|♓', raw_text, maxsplit=1)
    intro = intro_match[0].strip() if len(intro_match) > 1 else ""

    # 2. Знаходимо кінцівку (Порада та Афірмація)
    outro_match = re.split(r'✨\s*<b>Порада', raw_text, maxsplit=1)
    outro = "✨ <b>Порада" + outro_match[1].strip() if len(outro_match) > 1 else ""

    # 3. Витягуємо рядок для кожного конкретного знаку
    signs_mapping = {
        "aries": "Овен", "taurus": "Телець", "gemini": "Близнюки",
        "cancer": "Рак", "leo": "Лев", "virgo": "Діва",
        "libra": "Терези", "scorpio": "Скорпіон", "sagittarius": "Стрілець",
        "capricorn": "Козер", "aquarius": "Водолій", "pisces": "Риби"
    }
    
    user_horoscopes = {"all": raw_text} # Для тих, хто не обрав знак
    
    lines = raw_text.split('\n')
    for key, name in signs_mapping.items():
        sign_line = ""
        for line in lines:
            if name in line and ("-" in line or "—" in line):
                sign_line = line.strip()
                break
        
        # Склеюємо персональний гороскоп: Вступ + Конкретний знак + Кінцівка
        if sign_line and outro:
            user_horoscopes[key] = f"{intro}\n\n{sign_line}\n\n{outro}"
        else:
            user_horoscopes[key] = raw_text # Запасний варіант

    # === РОЗСИЛКА КОРИСТУВАЧАМ ===
    users_ref = db.collection("users").stream()
    count = 0
    
    for doc in users_ref:
        user_data = doc.to_dict() or {}
        user_id = doc.id
        
        # Беремо знак юзера (або "all" за замовчуванням)
        zodiac_pref = user_data.get("zodiac_sign", "all")
        text_to_send = user_horoscopes.get(zodiac_pref, user_horoscopes["all"])
        
        final_message = f"🔮 <b>Щоденний Кармічний Гороскоп</b>\n\n{text_to_send}"
        
        try:
            # 1. Відправляємо ТЕКСТ гороскопу (БЕЗ МЕНЮ, щоб він не зникав)
            await bot.send_message(
                chat_id=user_id, 
                text=final_message, 
                parse_mode="HTML"
            )
            
            # 2. Відправляємо МЕНЮ окремим маленьким повідомленням під гороскопом
            await bot.send_message(
                chat_id=user_id, 
                text="💫 <i>Що підказує твоя інтуїція далі?</i> 👇", 
                reply_markup=horoscope_share_menu_kb(),
                parse_mode="HTML"
            )
            count += 1
            await asyncio.sleep(0.1) # Захист від блокування
        except Exception:
            pass

    logging.info(f"Гороскоп успішно надіслано {count} користувачам.")