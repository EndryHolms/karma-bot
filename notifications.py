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

import logging
import asyncio
from datetime import datetime
import pytz
from aiogram import Bot
from firebase_admin import firestore
from keyboards import horoscope_share_menu_kb

async def send_daily_horoscope(bot: Bot, db: firestore.Client, tarot_model):
    logging.info("Починаю генерацію та розсилку гороскопів...")
    
    # 🕒 Отримуємо сьогоднішню дату (за Києвом) у форматі "09.03"
    tz = pytz.timezone('Europe/Kyiv')
    today_date = datetime.now(tz).strftime("%d.%m")
    
    # 👇 Оновлений, максимально короткий промпт
    prompt = (
        "Напиши іронічний, кумедний та дуже життєвий гороскоп на сьогодні для всіх 12 знаків зодіаку (по одному короткому реченню). "
        "Стиль: сарказм, втома від роботи, жарти про гроші, погоду та стосунки. "
        "СУВОРА УМОВА: Жодного тексту до чи після знаків! Без вступів, без висновків, без зірочок Markdown. "
        "Тільки 12 рядків. Обов'язково роби порожній рядок (Enter) між знаками. "
        "Формат має бути точно таким:\n"
        "♈ Овен - [твій жарт]\n\n"
        "♉ Телець - [твій жарт]\n\n"
        "...і так для всіх 12 знаків."
    )
    
    try:
        response = await asyncio.to_thread(tarot_model.generate_content, prompt)
        raw_text = getattr(response, "text", "").strip()
    except Exception as e:
        logging.error(f"Помилка генерації гороскопу: {e}")
        return

    if not raw_text:
        return

    # === ЛОГІКА РОЗДІЛЕННЯ ТЕКСТУ ===
    signs_mapping = {
        "aries": "Овен", "taurus": "Телець", "gemini": "Близнюки",
        "cancer": "Рак", "leo": "Лев", "virgo": "Діва",
        "libra": "Терези", "scorpio": "Скорпіон", "sagittarius": "Стрілець",
        "capricorn": "Козер", "aquarius": "Водолій", "pisces": "Риби"
    }
    
    user_horoscopes = {"all": raw_text} # Якщо юзер обрав "Всі знаки"
    
    lines = raw_text.split('\n')
    for key, name in signs_mapping.items():
        sign_line = ""
        for line in lines:
            if name in line and ("-" in line or "—" in line):
                sign_line = line.strip()
                break
        
        # Якщо юзер обрав конкретний знак, він отримає ТІЛЬКИ цей рядок
        user_horoscopes[key] = sign_line if sign_line else raw_text

    # === РОЗСИЛКА КОРИСТУВАЧАМ ===
    users_ref = db.collection("users").stream()
    count = 0
    
    for doc in users_ref:
        user_data = doc.to_dict() or {}
        user_id = doc.id
        
        zodiac_pref = user_data.get("zodiac_sign", "all")
        text_to_send = user_horoscopes.get(zodiac_pref, user_horoscopes["all"])
        
        # 👇 Додаємо наш новий лаконічний заголовок з датою
        final_message = f"🔮 <b>Кармічний гороскоп на {today_date}:</b>\n\n{text_to_send}"
        
        try:
            # 1. Відправляємо текст
            await bot.send_message(
                chat_id=user_id, 
                text=final_message, 
                parse_mode="HTML"
            )
            
            # 2. Відправляємо меню
            await bot.send_message(
                chat_id=user_id, 
                text="💫 <i>Що підказує твоя інтуїція далі?</i> 👇", 
                reply_markup=horoscope_share_menu_kb(),
                parse_mode="HTML"
            )
            count += 1
            await asyncio.sleep(0.1)
        except Exception:
            pass

    logging.info(f"Гороскоп успішно надіслано {count} користувачам.")