"""
Обработка выбора времени и финальная публикация
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramAPIError

from config import Config
from database import get_news, update_news_status, record_stat
from keyboards import published_keyboard

router = Router()
logger = logging.getLogger(__name__)

# Хранилище ожидающих ввода времени: {admin_id: news_id}
_waiting_custom_time: dict = {}


@router.callback_query(F.data.startswith("time:"))
async def on_time_select(call: CallbackQuery, bot: Bot):
    parts = call.data.split(":")
    # time:now:123  or  time:60:123  or  time:custom:123  or time:eve:123
    action = parts[1]
    news_id = int(parts[2])

    news = get_news(news_id)
    if not news:
        await call.answer("Новость не найдена", show_alert=True)
        return

    if action == "custom":
        _waiting_custom_time[call.from_user.id] = news_id
        await call.answer()
        await call.message.reply(
            "⌨️ Введи время публикации в формате <b>ЧЧ:ММ</b> (по Минску)\n"
            "Например: <code>18:30</code>",
            parse_mode="HTML"
        )
        return

    # Вычисляем время
    now_minsk = datetime.now(timezone.utc) + timedelta(hours=3)

    if action == "now":
        scheduled_at = datetime.now(timezone.utc).isoformat()
        label = "⚡ Публикуется сейчас"
    elif action == "eve":
        target = now_minsk.replace(hour=20, minute=0, second=0, microsecond=0)
        if target <= now_minsk:
            target += timedelta(days=1)
        scheduled_at = (target - timedelta(hours=3)).isoformat()  # в UTC
        label = f"📅 Запланировано на 20:00"
    else:
        minutes = int(action)
        target_utc = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        scheduled_at = target_utc.isoformat()
        label = f"⏰ Запланировано через {minutes} мин"

    update_news_status(news_id, "scheduled", scheduled_at=scheduled_at)

    await call.message.edit_reply_markup(reply_markup=published_keyboard())
    await call.answer(label)

    # Обновляем заголовок сообщения
    try:
        old = call.message.caption or call.message.text or ""
        new_text = f"🕐 <i>{label}</i>\n\n" + old
        if call.message.photo:
            await call.message.edit_caption(caption=new_text[:1024], parse_mode="HTML")
        else:
            await call.message.edit_text(text=new_text[:4096], parse_mode="HTML",
                                          disable_web_page_preview=True)
    except Exception:
        pass

    if action == "now":
        await _do_publish(bot, news_id)


async def _do_publish(bot: Bot, news_id: int):
    """Фактическая отправка в канал"""
    from config import Config
    config = Config.load()

    news = get_news(news_id)
    if not news:
        return

    title = news.get("title", "")
    text = news.get("text", "")
    url = news.get("url", "")
    source = news.get("source_name", "")
    image_url = news.get("image_url")

    post_text = (
        f"<b>{title}</b>\n\n"
        f"{text[:1800]}\n\n"
        f"🔗 <a href='{url}'>{source}</a>"
    )

    try:
        if image_url and image_url.startswith("http"):
            await bot.send_photo(
                chat_id=config.CHANNEL_ID,
                photo=image_url,
                caption=post_text,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=config.CHANNEL_ID,
                text=post_text,
                parse_mode="HTML"
            )

        now_str = datetime.now().isoformat()
        update_news_status(news_id, "published", published_at=now_str)
        record_stat(news["source_name"], news["source_type"], "published")
        logger.info(f"Опубликована новость #{news_id}")
    except TelegramAPIError as e:
        logger.error(f"Publish error: {e}")


@router.message(F.text.regexp(r"^\d{1,2}:\d{2}$"))
async def on_custom_time(msg: Message, bot: Bot):
    """Обрабатываем ввод времени в формате ЧЧ:ММ"""
    admin_id = msg.from_user.id
    news_id = _waiting_custom_time.pop(admin_id, None)
    if not news_id:
        return

    try:
        h, m = map(int, msg.text.strip().split(":"))
        now_minsk = datetime.now(timezone.utc) + timedelta(hours=3)
        target = now_minsk.replace(hour=h, minute=m, second=0, microsecond=0)
        if target <= now_minsk:
            target += timedelta(days=1)
        scheduled_utc = (target - timedelta(hours=3)).isoformat()

        update_news_status(news_id, "scheduled", scheduled_at=scheduled_utc)
        await msg.reply(
            f"✅ Новость #{news_id} запланирована на <b>{h:02d}:{m:02d}</b> (по Минску)",
            parse_mode="HTML"
        )
    except ValueError:
        _waiting_custom_time[admin_id] = news_id
        await msg.reply("❌ Неверный формат. Используй ЧЧ:ММ, например: <code>18:30</code>",
                        parse_mode="HTML")
