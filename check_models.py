import os
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

for m in client.models.list():
    # виведе назву моделі + що вона вміє
    print(m.name, getattr(m, "supported_actions", None))
