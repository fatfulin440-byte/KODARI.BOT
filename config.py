import os
from dotenv import load_dotenv
from pykodaribot import Bot

load_dotenv()

BOT_TOKEN = os.getenv("KODARI_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Ошибка: не найден KODARI_BOT_TOKEN в файле .env")

bot = Bot(token=BOT_TOKEN)
