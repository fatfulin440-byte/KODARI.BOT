import asyncio
from pykodaribot import Dispatcher, BotCommand
from config import bot
from handlers.user import router as user_router


async def main():
    dp = Dispatcher()
    dp.include_router(user_router)

    print("Бот-справочник запущен в щадящем режиме (1 запрос/сек)!")
    offset = 0

    while True:
        try:
            # Запрашиваем обновления не чаще 1 раза в секунду
            updates = await bot.get_updates(offset=offset, timeout=10)
            for upd in updates:
                offset = upd.update_id + 1
                await dp.feed_update(bot, upd)
        except Exception as e:
            err_text = str(e)
            if "429" in err_text:
                print("Лимит запросов 429 от сервера. Ждём 10 секунд...")
                await asyncio.sleep(10)
            else:
                print(f"Ошибка сети: {err_text}")
                await asyncio.sleep(2)

        await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(main())
