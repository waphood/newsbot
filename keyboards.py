"""
Клавиатуры (InlineKeyboard)
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def review_keyboard(news_id: int) -> InlineKeyboardMarkup:
    """Кнопки первичного просмотра: Опубликовать / Редактировать / Пропустить"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"pub:{news_id}"),
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{news_id}"),
        ],
        [
            InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip:{news_id}"),
        ]
    ])


def time_keyboard(news_id: int) -> InlineKeyboardMarkup:
    """Выбор времени публикации"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ Сейчас",     callback_data=f"time:now:{news_id}"),
            InlineKeyboardButton(text="⏰ +30 мин",    callback_data=f"time:30:{news_id}"),
        ],
        [
            InlineKeyboardButton(text="🕐 +1 час",     callback_data=f"time:60:{news_id}"),
            InlineKeyboardButton(text="🕑 +2 часа",    callback_data=f"time:120:{news_id}"),
        ],
        [
            InlineKeyboardButton(text="🕕 +3 часа",    callback_data=f"time:180:{news_id}"),
            InlineKeyboardButton(text="📅 Сегодня вечером (20:00)", callback_data=f"time:eve:{news_id}"),
        ],
        [
            InlineKeyboardButton(text="⌨️ Ввести время вручную", callback_data=f"time:custom:{news_id}"),
        ]
    ])


def edit_keyboard(news_id: int) -> InlineKeyboardMarkup:
    """Кнопки при редактировании"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"pub:{news_id}"),
        ],
        [
            InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip:{news_id}"),
        ]
    ])


def published_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовано", callback_data="noop")]
    ])
