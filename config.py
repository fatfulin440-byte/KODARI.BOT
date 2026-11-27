import os
from aiogram import Bot

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

BOT_TOKEN = None

if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                if key.strip() in ("BOT_TOKEN", "KODARI_BOT_TOKEN"):
                    BOT_TOKEN = val.strip().strip('"').strip("'")
                    break

if not BOT_TOKEN:
    raise ValueError(f"Файл {ENV_PATH} пустой или в нём нет строки BOT_TOKEN=ваш_токен")

bot = Bot(token=BOT_TOKEN)
