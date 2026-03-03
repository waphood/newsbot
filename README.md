# 🗞 Gomel News Bot

Телеграм-бот для сбора, модерации и публикации новостей Гомеля.

---

## 📦 Установка

### 1. Клонируй / скопируй файлы на сервер или VPS

### 2. Установи зависимости

```bash
pip install -r requirements.txt
```

### 3. Настрой config.json

При первом запуске создаётся файл `config.json`. Открой его и заполни:

```json
{
  "BOT_TOKEN": "ВАШ_ТОКЕН_ОТ_BOTFATHER",
  "ADMIN_ID": 123456789,
  "CHANNEL_ID": "@твой_канал",
  "CHECK_INTERVAL": 30
}
```

- **BOT_TOKEN** — получить у @BotFather
- **ADMIN_ID** — твой Telegram ID (узнать у @userinfobot)
- **CHANNEL_ID** — @username твоего канала (бот должен быть администратором канала!)
- **CHECK_INTERVAL** — интервал проверки новостей в минутах

### 4. Запусти бота

```bash
python bot.py
```

---

## 📱 Мониторинг Telegram-каналов (опционально)

Для мониторинга ТГ-каналов нужно Telethon API:

1. Зайди на [my.telegram.org](https://my.telegram.org)
2. Создай приложение — получишь `api_id` и `api_hash`
3. Добавь в `config.json`:

```json
{
  "TG_API_ID": 1234567,
  "TG_API_HASH": "abcdef1234567890",
  ...
}
```

4. Добавляй каналы командой `/addchannel @channel_username`

---

## 🤖 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и список команд |
| `/sources` | Список сайтов-источников |
| `/channels` | Список ТГ-каналов |
| `/addchannel @channel` | Добавить ТГ-канал |
| `/delchannel @channel` | Удалить ТГ-канал |
| `/stats` | Статистика за 30 дней |
| `/check` | Проверить новости сейчас |
| `/interval 30` | Изменить интервал проверки |

---

## 🔄 Процесс работы

```
Бот парсит сайты / ТГ-каналы
        ↓
Присылает тебе новость с кнопками
        ↓
┌──────────────────────────────────┐
│  ✅ Опубликовать                 │
│  ✏️ Редактировать                │
│  ⏭ Пропустить                   │
└──────────────────────────────────┘
        ↓
При "Опубликовать" — выбор времени:
  ⚡ Сейчас | ⏰ +30мин | 🕐 +1ч | 📅 Вечером | Вручную
        ↓
При "Редактировать" — отвечаешь текстом (+ фото)
  → Появляется превью с кнопкой публикации
        ↓
При "Пропустить" — записывается в статистику
```

---

## 📊 Статистика

`/stats` показывает:
- Сколько опубликовано / пропущено / отредактировано за 30 дней
- Топ сайтов по количеству новостей
- Топ ТГ-каналов по количеству новостей

---

## 🚀 Автозапуск (systemd на Linux)

Создай файл `/etc/systemd/system/gomel-bot.service`:

```ini
[Unit]
Description=Gomel News Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/gomel_news_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable gomel-bot
systemctl start gomel-bot
systemctl status gomel-bot
```
