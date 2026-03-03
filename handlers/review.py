"""
Обработка кнопок: Опубликовать / Редактировать / Пропустить
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from database import get_news, update_news_status, record_stat
from keyboards import time_keyboard, edit_keyboard

router = Router()


@router.callback_query(F.data.startswith("pub:"))
async def on_publish(call: CallbackQuery):
    news_id = int(call.data.split(":")[1])
    news = get_news(news_id)
    if not news:
        await call.answer("Новость не найдена", show_alert=True)
        return

    await call.message.edit_reply_markup(reply_markup=time_keyboard(news_id))
    await call.answer("Выбери время публикации 👇")


@router.callback_query(F.data.startswith("skip:"))
async def on_skip(call: CallbackQuery):
    news_id = int(call.data.split(":")[1])
    news = get_news(news_id)
    if not news:
        await call.answer("Новость не найдена", show_alert=True)
        return

    update_news_status(news_id, "skipped")
    record_stat(news["source_name"], news["source_type"], "skipped")

    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer("⏭ Пропущено — добавлено в статистику")

    # Зачёркиваем или помечаем
    try:
        old = call.message.caption or call.message.text or ""
        new_text = "⏭ <i>Пропущено</i>\n\n" + old
        if call.message.photo:
            await call.message.edit_caption(caption=new_text[:1024], parse_mode="HTML")
        else:
            await call.message.edit_text(text=new_text[:4096], parse_mode="HTML",
                                          disable_web_page_preview=True)
    except Exception:
        pass


@router.callback_query(F.data.startswith("edit:"))
async def on_edit(call: CallbackQuery):
    news_id = int(call.data.split(":")[1])
    news = get_news(news_id)
    if not news:
        await call.answer("Новость не найдена", show_alert=True)
        return

    await call.answer()
    await call.message.reply(
        f"✏️ <b>Режим редактирования</b>\n\n"
        f"Отправь новый текст новости в ответ на это сообщение.\n"
        f"Можешь добавить фото — просто прикрепи его к тексту.\n\n"
        f"<i>news_id: {news_id}</i>",
        parse_mode="HTML"
    )
    # Сохраняем состояние — ждём ответ
    update_news_status(news_id, "editing")


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()
