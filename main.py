import asyncio
from aiogram import Dispatcher
from aiogram.types import BotCommand
from config import bot
from handlers.user import router as user_router


async def main():
    dp = Dispatcher()
    dp.include_router(user_router)

    await bot.set_my_commands([
        BotCommand(command="start", description="Открыть справочник 9–11 классов"),
    ])

    print("Telegram-бот справочник успешно запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
