"""
Мониторинг Telegram-каналов через Telethon
"""
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from telethon import TelegramClient
    from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    logger.warning("Telethon не установлен — мониторинг ТГ-каналов недоступен")


class TGMonitor:
    def __init__(self, api_id: int, api_hash: str, session_name: str = "tg_monitor"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.client: Optional["TelegramClient"] = None

    async def connect(self):
        if not TELETHON_AVAILABLE:
            return False
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        await self.client.start()
        return True

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()

    async def fetch_channel_news(self, channel_username: str, limit: int = 10,
                                  hours_back: int = 2) -> List[Dict]:
        """Получаем последние посты из канала"""
        if not self.client:
            return []

        since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        results = []

        try:
            entity = await self.client.get_entity(channel_username)
            messages = await self.client.get_messages(entity, limit=limit)

            for msg in messages:
                if not msg.date or msg.date < since:
                    continue
                if not msg.text and not msg.caption:
                    continue

                text = msg.text or msg.caption or ""
                if len(text) < 20:
                    continue

                # Картинки
                images = []
                image_url = None

                # Если медиа-группа (альбом) — берём все картинки
                if msg.grouped_id:
                    # Пометим для последующей загрузки
                    images = [f"tg://msg/{msg.id}/photo"]
                elif isinstance(msg.media, MessageMediaPhoto):
                    images = [f"tg://msg/{msg.id}/photo"]

                if images:
                    image_url = images[0]

                # Уникальный URL
                ch_name = channel_username.lstrip("@")
                url = f"https://t.me/{ch_name}/{msg.id}"

                results.append({
                    "source_name": channel_username,
                    "source_type": "tg",
                    "title": text[:100],
                    "text": text[:2000],
                    "url": url,
                    "image_url": image_url,
                    "images": images,
                    "_tg_msg": msg,           # Сырой объект для скачивания фото
                })
        except Exception as e:
            logger.error(f"TG fetch error {channel_username}: {e}")

        return results

    async def download_photo(self, msg, path: str) -> Optional[str]:
        """Скачиваем фото из сообщения на диск"""
        if not self.client:
            return None
        try:
            file = await self.client.download_media(msg, file=path)
            return file
        except Exception as e:
            logger.error(f"Photo download error: {e}")
            return None

    async def fetch_all_channels(self, channels: List[dict]) -> List[Dict]:
        results = []
        for ch in channels:
            if not ch.get("enabled", True):
                continue
            username = ch.get("username", "")
            if not username:
                continue
            news = await self.fetch_channel_news(username)
            results.extend(news)
        return results
