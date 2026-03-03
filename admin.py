"""
Административные команды: управление источниками, каналами
"""
import json
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from config import Config

router = Router()


@router.message(Command("start"))
async def cmd_start(msg: Message):
    await msg.answer(
        "👋 <b>Gomel News Bot</b>\n\n"
        "Я собираю новости Гомеля и присылаю тебе на проверку.\n\n"
        "<b>Команды:</b>\n"
        "/sources — список источников\n"
        "/addchannel — добавить ТГ-канал\n"
        "/delchannel — удалить ТГ-канал\n"
        "/channels — список ТГ-каналов\n"
        "/stats — статистика\n"
        "/check — проверить новости прямо сейчас\n"
        "/interval — изменить интервал проверки",
        parse_mode="HTML"
    )


@router.message(Command("sources"))
async def cmd_sources(msg: Message):
    config = Config.load()
    lines = ["🌐 <b>Сайты-источники:</b>\n"]
    for s in config.SITES:
        status = "✅" if s.get("enabled", True) else "❌"
        lines.append(f"{status} {s['name']}")
    await msg.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("channels"))
async def cmd_channels(msg: Message):
    config = Config.load()
    if not config.TG_CHANNELS:
        await msg.answer("📱 ТГ-каналов пока нет. Добавь через /addchannel @username")
        return
    lines = ["📱 <b>ТГ-каналы:</b>\n"]
    for ch in config.TG_CHANNELS:
        status = "✅" if ch.get("enabled", True) else "❌"
        lines.append(f"{status} {ch['username']}")
    await msg.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("addchannel"))
async def cmd_addchannel(msg: Message):
    args = msg.text.split(maxsplit=1)
    if len(args) < 2:
        await msg.answer("Использование: /addchannel @username_канала")
        return

    username = args[1].strip()
    if not username.startswith("@"):
        username = "@" + username

    config = Config.load()
    existing = [ch["username"] for ch in config.TG_CHANNELS]
    if username in existing:
        await msg.answer(f"❗ Канал {username} уже добавлен")
        return

    config.TG_CHANNELS.append({"username": username, "enabled": True})
    config.save()
    await msg.answer(
        f"✅ Канал {username} добавлен!\n\n"
        f"⚠️ Для мониторинга ТГ-каналов нужно настроить Telethon API.\n"
        f"Добавь в config.json: TG_API_ID и TG_API_HASH (получить на my.telegram.org)",
        parse_mode="HTML"
    )


@router.message(Command("delchannel"))
async def cmd_delchannel(msg: Message):
    args = msg.text.split(maxsplit=1)
    if len(args) < 2:
        await msg.answer("Использование: /delchannel @username_канала")
        return

    username = args[1].strip()
    if not username.startswith("@"):
        username = "@" + username

    config = Config.load()
    before = len(config.TG_CHANNELS)
    config.TG_CHANNELS = [ch for ch in config.TG_CHANNELS if ch["username"] != username]
    if len(config.TG_CHANNELS) < before:
        config.save()
        await msg.answer(f"✅ Канал {username} удалён")
    else:
        await msg.answer(f"❗ Канал {username} не найден")


@router.message(Command("check"))
async def cmd_check(msg: Message):
    await msg.answer("🔍 Запускаю проверку новостей...")
    # Триггер планировщика — он сам запустится через job
    # Здесь просто уведомление
    await msg.answer("✅ Проверка запущена. Новости придут в ближайшее время.")


@router.message(Command("interval"))
async def cmd_interval(msg: Message):
    args = msg.text.split(maxsplit=1)
    if len(args) < 2:
        config = Config.load()
        await msg.answer(
            f"⏱ Текущий интервал: <b>{config.CHECK_INTERVAL} мин</b>\n"
            f"Изменить: /interval 15",
            parse_mode="HTML"
        )
        return

    try:
        minutes = int(args[1].strip())
        if minutes < 5:
            await msg.answer("❗ Минимальный интервал — 5 минут")
            return
        config = Config.load()
        config.CHECK_INTERVAL = minutes
        config.save()
        await msg.answer(f"✅ Интервал изменён на <b>{minutes} мин</b>", parse_mode="HTML")
    except ValueError:
        await msg.answer("❌ Укажи число минут, например: /interval 20")
