"""
Планировщик: периодически парсит новости и отправляет на проверку
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from config import Config
from parsers import fetch_all_sites
from database import init_db, news_exists, add_news, get_scheduled_news, update_news_status
from keyboards import review_keyboard

logger = logging.getLogger(__name__)


class NewsScheduler:
    def __init__(self, bot: Bot, config: Config):
        self.bot = bot
        self.config = config
        self.scheduler = AsyncIOScheduler(timezone="Europe/Minsk")
        self._tg_monitor = None

        init_db()

    def start(self):
        self.scheduler.add_job(
            self.fetch_and_send,
            "interval",
            minutes=self.config.CHECK_INTERVAL,
            id="news_fetch",
            next_run_time=datetime.now()
        )
        self.scheduler.add_job(
            self.publish_scheduled,
            "interval",
            minutes=1,
            id="scheduled_publish"
        )
        self.scheduler.start()
        logger.info("Планировщик запущен")

    async def fetch_and_send(self):
        logger.info("Проверяем новости...")
        all_news = []

        # Сайты
        try:
            site_news = await fetch_all_sites(self.config.SITES)
            all_news.extend(site_news)
        except Exception as e:
            logger.error(f"Site fetch error: {e}")

        # ТГ-каналы (если настроены)
        if self.config.TG_CHANNELS and hasattr(self.config, "TG_API_ID"):
            try:
                from tg_monitor import TGMonitor
                monitor = TGMonitor(self.config.TG_API_ID, self.config.TG_API_HASH)
                if await monitor.connect():
                    tg_news = await monitor.fetch_all_channels(self.config.TG_CHANNELS)
                    all_news.extend(tg_news)
                    await monitor.disconnect()
            except Exception as e:
                logger.error(f"TG monitor error: {e}")

        new_count = 0
        for item in all_news:
            url = item.get("url", "")
            if not url or news_exists(url):
                continue

            news_id = add_news(
                source_name=item["source_name"],
                source_type=item["source_type"],
                title=item.get("title", ""),
                text=item.get("text", ""),
                url=url,
                image_url=item.get("image_url"),
                images=item.get("images", []),
            )
            if news_id:
                await self.send_review(news_id, item)
                new_count += 1
                await asyncio.sleep(0.5)  # антифлуд

        if new_count:
            logger.info(f"Отправлено на проверку: {new_count} новостей")

    async def send_review(self, news_id: int, item: dict):
        """Отправляем новость администратору на проверку"""
        from keyboards import review_keyboard

        source = item["source_name"]
        source_type = "🌐" if item["source_type"] == "site" else "📱"
        title = item.get("title", "Без заголовка")
        text = item.get("text", "")
        url = item.get("url", "")
        image_url = item.get("image_url")

        caption = (
            f"{source_type} <b>{source}</b>\n\n"
            f"<b>{title}</b>\n\n"
            f"{text[:600]}{'...' if len(text) > 600 else ''}\n\n"
            f"🔗 <a href='{url}'>Источник</a>"
        )

        kb = review_keyboard(news_id)

        try:
            if image_url and image_url.startswith("http"):
                msg = await self.bot.send_photo(
                    chat_id=self.config.ADMIN_ID,
                    photo=image_url,
                    caption=caption,
                    reply_markup=kb,
                    parse_mode="HTML"
                )
            else:
                msg = await self.bot.send_message(
                    chat_id=self.config.ADMIN_ID,
                    text=caption,
                    reply_markup=kb,
                    parse_mode="HTML",
                    disable_web_page_preview=False
                )
            # Сохраняем message_id для последующего редактирования
            update_news_status(news_id, "pending", message_id=msg.message_id)
        except TelegramAPIError as e:
            logger.error(f"Send review error: {e}")

    async def publish_scheduled(self):
        """Публикуем запланированные новости"""
        from keyboards import published_keyboard

        now = datetime.now(timezone.utc)
        for item in get_scheduled_news():
            scheduled_at = item.get("scheduled_at")
            if not scheduled_at:
                continue
            try:
                sched_dt = datetime.fromisoformat(scheduled_at)
                if sched_dt.tzinfo is None:
                    from datetime import timezone as tz
                    sched_dt = sched_dt.replace(tzinfo=tz.utc)
            except Exception:
                continue

            if now >= sched_dt:
                await self._publish_item(item)

    async def _publish_item(self, item: dict):
        """Публикуем новость в канал"""
        news_id = item["id"]
        text = item.get("text", "")
        title = item.get("title", "")
        image_url = item.get("image_url")
        source = item.get("source_name", "")
        url = item.get("url", "")

        post_text = (
            f"<b>{title}</b>\n\n"
            f"{text[:1800]}\n\n"
            f"🔗 <a href='{url}'>{source}</a>"
        )

        try:
            if image_url and image_url.startswith("http"):
                await self.bot.send_photo(
                    chat_id=self.config.CHANNEL_ID,
                    photo=image_url,
                    caption=post_text,
                    parse_mode="HTML"
                )
            else:
                await self.bot.send_message(
                    chat_id=self.config.CHANNEL_ID,
                    text=post_text,
                    parse_mode="HTML"
                )

            now_str = datetime.now().isoformat()
            update_news_status(news_id, "published", published_at=now_str)
            from database import record_stat
            record_stat(item["source_name"], item["source_type"], "published")
            logger.info(f"Опубликована новость #{news_id}")
        except TelegramAPIError as e:
            logger.error(f"Publish error #{news_id}: {e}")
