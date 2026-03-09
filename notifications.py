import asyncio
import logging
from datetime import datetime

import pytz
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from firebase_admin import firestore

from keyboards import horoscope_share_menu_kb, main_menu_kb
from lexicon import get_text # Імпортуємо наш універсальний get_text


async def send_daily_reminders(bot: Bot, db: firestore.Client):
    logging.info("Починаю розсилку нагадувань...")
    today_str = datetime.now().strftime("%Y-%m-%d")

    users_ref = db.collection("users").stream()

    # Збираємо користувачів, групуючи за мовою
    users_by_lang = {"uk": [], "en": [], "ru": []}
    async for doc in users_ref:
        user_data = doc.to_dict()
        user_id = doc.id
        lang = user_data.get("language_code", "uk")
        last_date = user_data.get("last_daily_card_date")

        if last_date != today_str:
            if lang in users_by_lang:
                users_by_lang[lang].append(user_id)
            else:
                users_by_lang["uk"].append(user_id) # Фоллбек

    total_sent = 0
    for lang, user_ids in users_by_lang.items():
        if not user_ids:
            continue

        # Отримуємо локалізований текст нагадування
        text = get_text(lang, "daily_reminder_text")
        
        count = 0
        for user_id in user_ids:
            try:
                await bot.send_message(
                    chat_id=user_id, text=text, reply_markup=main_menu_kb(lang)
                )
                count += 1
                await asyncio.sleep(0.1)
            except TelegramForbiddenError:
                pass
            except Exception as e:
                logging.error(f"Помилка розсилки нагадування для {user_id}: {e}")
        logging.info(f"Нагадування надіслано {count} користувачам ({lang.upper()}).")
        total_sent += count
        
    logging.info(f"Всього нагадувань надіслано: {total_sent}.")


async def send_daily_horoscope(bot: Bot, db: firestore.Client, tarot_model):
    logging.info("Починаю генерацію та розсилку гороскопів...")

    users_ref = db.collection("users").stream()
    users_by_lang = {"uk": [], "en": [], "ru": []}
    
    # 1. Збираємо всіх активних користувачів і групуємо їх за мовою
    async for doc in users_ref:
        user_data = doc.to_dict() or {}
        lang = user_data.get("language_code", "uk")
        zodiac_pref = user_data.get("zodiac_sign", "all")
        if lang in users_by_lang:
            users_by_lang[lang].append((doc.id, zodiac_pref))
        else:
            users_by_lang["uk"].append((doc.id, zodiac_pref)) # Фоллбек

    tz = pytz.timezone("Europe/Kyiv")
    today_date = datetime.now(tz).strftime("%d.%m")

    # 2. Генеруємо і розсилаємо гороскоп для кожної мовної групи окремо
    for lang, users in users_by_lang.items():
        if not users:
            continue

        logging.info(f"Генерую гороскоп для {len(users)} користувачів ({lang.upper()})...")

        # Динамічно отримуємо системну інструкцію та промпт для потрібної мови
        system_instruction = get_text(lang, "karma_system_prompt")
        prompt = get_text(lang, "horoscope_generation_prompt")
        
        raw_text = ""
        try:
            # Використовуємо наш новий `generate_content` з інструкцією
            response = await asyncio.to_thread(
                tarot_model.generate_content, 
                prompt, 
                system_instruction=system_instruction
            )
            raw_text = getattr(response, "text", "").strip()
        except Exception as e:
            logging.error(f"Помилка генерації гороскопу для мови '{lang}': {e}")
            continue # Пропускаємо цю мову, якщо генерація впала

        if not raw_text:
            logging.warning(f"Модель повернула порожню відповідь для мови '{lang}'.")
            continue

        # 3. Розбираємо відповідь моделі
        zodiac_signs_map = get_text(lang, "zodiac_signs")
        user_horoscopes = {"all": raw_text} # Для тих, хто хоче бачити всі знаки
        
        lines = raw_text.split('\n')
        for key, name in zodiac_signs_map.items():
            sign_line = ""
            for line in lines:
                # Шукаємо точну назву знаку на початку рядка
                if line.strip().startswith(name):
                    sign_line = line.strip()
                    break
            user_horoscopes[key] = sign_line if sign_line else raw_text

        # 4. Розсилаємо згенерований текст
        count = 0
        for user_id, zodiac_pref in users:
            text_to_send = user_horoscopes.get(zodiac_pref, user_horoscopes["all"])
            final_message = get_text(lang, "horoscope_final_message").format(
                date=today_date, text=text_to_send
            )
            
            try:
                await bot.send_message(
                    chat_id=user_id, text=final_message, parse_mode="HTML"
                )
                await bot.send_message(
                    chat_id=user_id,
                    text=get_text(lang, "horoscope_intuition_prompt"),
                    reply_markup=horoscope_share_menu_kb(lang),
                    parse_mode="HTML",
                )
                count += 1
                await asyncio.sleep(0.1)
            except TelegramForbiddenError:
                pass # Користувач заблокував бота
            except Exception as e:
                logging.error(f"Помилка розсилки гороскопу для {user_id}: {e}")
        logging.info(f"Гороскоп успішно надіслано {count} користувачам ({lang.upper()}).")
