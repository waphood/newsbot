"""
Конфигурация бота.
На Railway — через переменные окружения.
Локально — через config.json (создаётся автоматически).
"""
import json
import os
from dataclasses import dataclass, field
from typing import List

CONFIG_FILE = "config.json"

DEFAULT_SITES = [
    {"name": "gomel.today",  "url": "https://gomel.today",   "type": "site", "enabled": True},
    {"name": "nashgomel.by", "url": "https://nashgomel.by",  "type": "site", "enabled": True},
    {"name": "newsgomel.by", "url": "https://newsgomel.by",  "type": "site", "enabled": True},
    {"name": "gp.by",        "url": "https://gp.by",         "type": "site", "enabled": True},
    {"name": "onliner.by",   "url": "https://onliner.by",    "type": "site", "enabled": True, "filter": "гомел"},
    {"name": "sb.by",        "url": "https://www.sb.by",     "type": "site", "enabled": True, "filter": "гомел"},
    {"name": "belta.by",     "url": "https://belta.by",      "type": "site", "enabled": True, "filter": "гомел"},
]


@dataclass
class Config:
    BOT_TOKEN: str = ""
    ADMIN_ID: int = 0
    CHANNEL_ID: str = "@your_channel"
    CHECK_INTERVAL: int = 30
    TG_API_ID: int = 0
    TG_API_HASH: str = ""
    SITES: List[dict] = field(default_factory=lambda: list(DEFAULT_SITES))
    TG_CHANNELS: List[dict] = field(default_factory=list)

    @classmethod
    def load(cls) -> "Config":
        cfg = cls()

        # 1. Сначала читаем config.json (если есть — для локальной разработки)
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, val in data.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, val)

        # 2. Переменные окружения перекрывают config.json (Railway / production)
        if os.environ.get("BOT_TOKEN"):
            cfg.BOT_TOKEN = os.environ["BOT_TOKEN"]
        if os.environ.get("ADMIN_ID"):
            cfg.ADMIN_ID = int(os.environ["ADMIN_ID"])
        if os.environ.get("CHANNEL_ID"):
            cfg.CHANNEL_ID = os.environ["CHANNEL_ID"]
        if os.environ.get("CHECK_INTERVAL"):
            cfg.CHECK_INTERVAL = int(os.environ["CHECK_INTERVAL"])
        if os.environ.get("TG_API_ID"):
            cfg.TG_API_ID = int(os.environ["TG_API_ID"])
        if os.environ.get("TG_API_HASH"):
            cfg.TG_API_HASH = os.environ["TG_API_HASH"]
        # TG_CHANNELS через env: JSON-строка, например '[{"username":"@gomel_news","enabled":true}]'
        if os.environ.get("TG_CHANNELS"):
            try:
                cfg.TG_CHANNELS = json.loads(os.environ["TG_CHANNELS"])
            except Exception:
                pass

        if not cfg.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не задан! Укажи в config.json или переменной окружения.")

        return cfg

    def save(self):
        """Сохраняем только для локальной разработки"""
        data = {
            "BOT_TOKEN": self.BOT_TOKEN,
            "ADMIN_ID": self.ADMIN_ID,
            "CHANNEL_ID": self.CHANNEL_ID,
            "CHECK_INTERVAL": self.CHECK_INTERVAL,
            "TG_API_ID": self.TG_API_ID,
            "TG_API_HASH": self.TG_API_HASH,
            "SITES": self.SITES,
            "TG_CHANNELS": self.TG_CHANNELS,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
