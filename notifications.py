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