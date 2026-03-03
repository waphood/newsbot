"""
Обработка режима редактирования новости
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message

from database import get_news, update_news_status
from keyboards import edit_keyboard

router = Router()
logger = logging.getLogger(__name__)

# {admin_id: news_id} — ожидаем отредактированный текст
_editing: dict = {}


def start_editing(admin_id: int, news_id: int):
    _editing[admin_id] = news_id


@router.message(F.reply_to_message & (F.text | F.photo))
async def on_edited_news(msg: Message, bot: Bot):
    """Ловим ответ на сообщение-подсказку редактирования"""
    admin_id = msg.from_user.id

    # Ищем news_id в тексте родительского сообщения (мы там написали news_id: XXX)
    reply = msg.reply_to_message
    if not reply:
        return

    reply_text = reply.text or reply.caption or ""
    if "news_id:" not in reply_text:
        return

    try:
        news_id = int(reply_text.split("news_id:")[-1].strip().split()[0])
    except (ValueError, IndexError):
        return

    news = get_news(news_id)
    if not news:
        await msg.reply("❌ Новость не найдена")
        return

    # Новый текст
    new_text = msg.caption or msg.text or news.get("text", "")
    new_image = None

    # Если прислали фото
    if msg.photo:
        new_image = msg.photo[-1].file_id  # file_id для переотправки

    # Сохраняем изменения
    update_news_status(
        news_id, "pending",
        text=new_text,
        image_url=new_image
    )

    # Отправляем превью отредактированной новости
    preview = (
        f"✏️ <b>Отредактированная версия</b>\n\n"
        f"{new_text[:1500]}\n\n"
        f"🔗 {news.get('url', '')}"
    )

    kb = edit_keyboard(news_id)

    if new_image:
        await msg.reply_photo(
            photo=new_image,
            caption=preview,
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        await msg.reply(
            text=preview,
            reply_markup=kb,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
