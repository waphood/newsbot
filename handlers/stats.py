"""
Статистика
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from database import get_stats_summary

router = Router()


@router.message(Command("stats"))
async def cmd_stats(msg: Message):
    data = get_stats_summary(days=30)
    total = data.get("total", {})

    published = total.get("published", 0)
    skipped   = total.get("skipped", 0)
    edited    = total.get("edited", 0)

    text = (
        "📊 <b>Статистика за 30 дней</b>\n\n"
        f"✅ Опубликовано: <b>{published}</b>\n"
        f"✏️ Отредактировано: <b>{edited}</b>\n"
        f"⏭ Пропущено: <b>{skipped}</b>\n\n"
    )

    # Топ сайтов
    top_sites = data.get("top_sites", [])
    if top_sites:
        text += "🌐 <b>Топ сайтов:</b>\n"
        for i, s in enumerate(top_sites, 1):
            text += f"  {i}. {s['name']} — {s['count']}\n"
        text += "\n"

    # Топ ТГ-каналов
    top_tg = data.get("top_tg", [])
    if top_tg:
        text += "📱 <b>Топ ТГ-каналов:</b>\n"
        for i, s in enumerate(top_tg, 1):
            text += f"  {i}. {s['name']} — {s['count']}\n"
    elif not top_sites:
        text += "<i>Данных пока нет</i>"

    await msg.answer(text, parse_mode="HTML")
