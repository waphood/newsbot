"""
Gomel News Bot — главный файл
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from handlers import review, publish, edit, stats, admin
from scheduler import NewsScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    config = Config.load()
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрируем роутеры
    dp.include_router(review.router)
    dp.include_router(publish.router)
    dp.include_router(edit.router)
    dp.include_router(stats.router)
    dp.include_router(admin.router)

    # Запускаем планировщик
    scheduler = NewsScheduler(bot, config)
    scheduler.start()

    logger.info("Бот запущен")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
