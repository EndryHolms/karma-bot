import google.generativeai as genai
import os
from dotenv import load_dotenv

# Завантажуємо змінні
load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")

# Налаштовуємо
genai.configure(api_key=api_key)

print(f"🔑 Ключ: {api_key[:5]}... (Перевіряю доступні моделі)")
print("-" * 30)

try:
    # Отримуємо список
    for m in genai.list_models():
        # Шукаємо тільки ті, що генерують текст
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ Доступна модель: {m.name}")
            
except Exception as e:
    print(f"❌ ПОМИЛКА: {e}")

print("-" * 30)