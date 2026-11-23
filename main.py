import asyncio
from pykodaribot import Dispatcher, BotCommand
from config import bot
from handlers.user import router as user_router


async def main():
    dp = Dispatcher()
    dp.include_router(user_router)

    # Перезаписываем список команд в меню бота (убирает старую /score)
    await bot.set_my_commands([
        BotCommand(command="start", description="Открыть справочник 9–11 классов")
    ])

    print("Бот-справочник запущен, меню команд обновлено!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
