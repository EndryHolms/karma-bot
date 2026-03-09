import asyncio
import logging
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
from keyboards import main_menu_kb, broadcast_horoscope_kb

# ... (тут твоя функція send_daily_reminders) ...

async def send_daily_horoscope(bot: Bot, db: firestore.Client, tarot_model):
    logging.info("Починаю генерацію та розсилку гороскопів...")
    
    prompt = (
        "Напиши іронічний, кумедний та дуже життєвий гороскоп на сьогодні для всіх 12 знаків зодіаку. "
        "Стиль: сарказм, втома від роботи, жарти про гроші, погоду та колишніх. Мінімум води. "
        "Формат строго такий: кожен знак з нового рядка, починається з емодзі, назви знаку та дефісу. Наприклад:\n"
        "♈ Овен - ви за здоровий спосіб життя, але сьогодні пʼятниця\n"
        "♉ Телець - ви повідомлення від колишніх так не чекали, як весну\n"
        "Згенеруй для всіх 12 знаків."
    )
    
    # 1. Запитуємо Gemini (всього 1 запит!)
    try:
        response = await asyncio.to_thread(tarot_model.generate_content, prompt)
        raw_text = getattr(response, "text", "").strip()
    except Exception as e:
        logging.error(f"Помилка генерації гороскопу: {e}")
        return

    if not raw_text:
        return

    # 2. Розбираємо текст по знаках
    signs_mapping = {
        "aries": "Овен", "taurus": "Телець", "gemini": "Близнюки",
        "cancer": "Рак", "leo": "Лев", "virgo": "Діва",
        "libra": "Терези", "scorpio": "Скорпіон", "sagittarius": "Стрілець",
        "capricorn": "Козер", "aquarius": "Водолій", "pisces": "Риби"
    }
    
    horoscope_dict = {"all": raw_text} # Для тих, хто хоче всі знаки
    
    # Шукаємо потрібний рядок для кожного знаку
    for key, ukr_name in signs_mapping.items():
        for line in raw_text.split('\n'):
            if ukr_name in line:
                horoscope_dict[key] = line.strip()
                break

    # 3. Робимо розсилку користувачам
    users_ref = db.collection("users").stream()
    count = 0
    
    for doc in users_ref:
        user_data = doc.to_dict()
        user_id = doc.id
        zodiac_pref = user_data.get("zodiac_sign", "all")
        
        # Визначаємо, що відправляти
        text_to_send = horoscope_dict.get(zodiac_pref)
        
        # Якщо чомусь не знайшли конкретний рядок, відправляємо загальний
        if not text_to_send:
            text_to_send = horoscope_dict["all"]

        final_message = f"🔮 <b>Щоденний Кармічний Гороскоп</b>\n\n{text_to_send}"
        
        # Якщо юзер отримує всі знаки, додаємо йому кнопку "Налаштувати свій"
        reply_markup = broadcast_horoscope_kb() if zodiac_pref == "all" else None

        try:
            await bot.send_message(chat_id=user_id, text=final_message, reply_markup=reply_markup)
            count += 1
            await asyncio.sleep(0.1) # Захист від блокування Телеграмом
        except Exception:
            pass # Юзер заблокував бота або видалив чат

    logging.info(f"Гороскоп успішно надіслано {count} користувачам.")