"""
База данных — PostgreSQL (Railway) или SQLite (локально).
Автоматически определяет по наличию переменной DATABASE_URL.
"""
import json
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
else:
    import sqlite3

DB_FILE = "news_bot.db"  # только для SQLite


# ─────────────────────────────────────────
# Подключение
# ─────────────────────────────────────────

def get_conn():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL, sslmode="require")
    else:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn


def _p() -> str:
    """Одиночный placeholder"""
    return "%s" if USE_POSTGRES else "?"


def _ph(n: int = 1) -> str:
    """N placeholders через запятую"""
    ph = "%s" if USE_POSTGRES else "?"
    return ", ".join([ph] * n)


def _fetchall(cursor) -> List[Dict]:
    if USE_POSTGRES:
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    return [dict(r) for r in cursor.fetchall()]


def _fetchone(cursor) -> Optional[Dict]:
    if USE_POSTGRES:
        row = cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))
    row = cursor.fetchone()
    return dict(row) if row else None


# ─────────────────────────────────────────
# Инициализация таблиц
# ─────────────────────────────────────────

def init_db():
    conn = get_conn()
    c = conn.cursor()

    id_col = "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"

    c.execute(f"""
        CREATE TABLE IF NOT EXISTS news (
            id           {id_col},
            source_name  TEXT NOT NULL,
            source_type  TEXT NOT NULL,
            title        TEXT,
            text         TEXT,
            url          TEXT UNIQUE,
            image_url    TEXT,
            images_json  TEXT,
            fetched_at   TEXT,
            status       TEXT DEFAULT 'pending',
            published_at TEXT,
            scheduled_at TEXT,
            message_id   INTEGER
        )
    """)

    c.execute(f"""
        CREATE TABLE IF NOT EXISTS stats (
            id           {id_col},
            date         TEXT NOT NULL,
            source_name  TEXT NOT NULL,
            source_type  TEXT NOT NULL,
            action       TEXT NOT NULL,
            count        INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()
    logger.info(f"БД инициализирована ({'PostgreSQL' if USE_POSTGRES else 'SQLite'})")


# ─────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────

def news_exists(url: str) -> bool:
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT id FROM news WHERE url={_p()}", (url,))
    row = c.fetchone()
    conn.close()
    return row is not None


def add_news(source_name: str, source_type: str, title: str, text: str,
             url: str, image_url: str = None, images: list = None) -> Optional[int]:
    conn = get_conn()
    c = conn.cursor()
    try:
        if USE_POSTGRES:
            c.execute("""
                INSERT INTO news (source_name, source_type, title, text, url, image_url, images_json, fetched_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (url) DO NOTHING
                RETURNING id
            """, (
                source_name, source_type, title, text, url, image_url,
                json.dumps(images or [], ensure_ascii=False),
                datetime.now().isoformat()
            ))
            row = c.fetchone()
            news_id = row[0] if row else None
        else:
            c.execute("""
                INSERT OR IGNORE INTO news
                (source_name, source_type, title, text, url, image_url, images_json, fetched_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                source_name, source_type, title, text, url, image_url,
                json.dumps(images or [], ensure_ascii=False),
                datetime.now().isoformat()
            ))
            news_id = c.lastrowid if c.rowcount else None
        conn.commit()
    except Exception as e:
        logger.error(f"add_news error: {e}")
        conn.rollback()
        news_id = None
    finally:
        conn.close()
    return news_id


def get_news(news_id: int) -> Optional[Dict]:
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT * FROM news WHERE id={_p()}", (news_id,))
    row = _fetchone(c)
    conn.close()
    return row


def update_news_status(news_id: int, status: str, published_at: str = None,
                       scheduled_at: str = None, message_id: int = None,
                       text: str = None, image_url: str = None):
    conn = get_conn()
    c = conn.cursor()
    p = _p()

    fields = [f"status={p}"]
    vals = [status]
    if published_at  is not None: fields.append(f"published_at={p}");  vals.append(published_at)
    if scheduled_at  is not None: fields.append(f"scheduled_at={p}");  vals.append(scheduled_at)
    if message_id    is not None: fields.append(f"message_id={p}");    vals.append(message_id)
    if text          is not None: fields.append(f"text={p}");          vals.append(text)
    if image_url     is not None: fields.append(f"image_url={p}");     vals.append(image_url)
    vals.append(news_id)

    c.execute(f"UPDATE news SET {', '.join(fields)} WHERE id={p}", vals)
    conn.commit()
    conn.close()


def record_stat(source_name: str, source_type: str, action: str):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()
    c = conn.cursor()
    p = _p()

    c.execute(
        f"SELECT id, count FROM stats WHERE date={p} AND source_name={p} AND action={p}",
        (today, source_name, action)
    )
    row = _fetchone(c)
    if row:
        c.execute(f"UPDATE stats SET count=count+1 WHERE id={p}", (row["id"],))
    else:
        c.execute(
            f"INSERT INTO stats (date, source_name, source_type, action) VALUES ({_ph(4)})",
            (today, source_name, source_type, action)
        )
    conn.commit()
    conn.close()


def get_stats_summary(days: int = 30) -> Dict:
    from datetime import timedelta
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    p = _p()
    conn = get_conn()
    c = conn.cursor()

    c.execute(f"SELECT action, SUM(count) as cnt FROM stats WHERE date>={p} GROUP BY action", (since,))
    total_rows = _fetchall(c)

    c.execute(f"""
        SELECT source_name, SUM(count) as cnt
        FROM stats WHERE date>={p} AND source_type='site'
        GROUP BY source_name ORDER BY cnt DESC LIMIT 10
    """, (since,))
    top_sites = _fetchall(c)

    c.execute(f"""
        SELECT source_name, SUM(count) as cnt
        FROM stats WHERE date>={p} AND source_type='tg'
        GROUP BY source_name ORDER BY cnt DESC LIMIT 10
    """, (since,))
    top_tg = _fetchall(c)

    conn.close()
    return {
        "total":     {r["action"]: r["cnt"] for r in total_rows},
        "top_sites": [{"name": r["source_name"], "count": r["cnt"]} for r in top_sites],
        "top_tg":    [{"name": r["source_name"], "count": r["cnt"]} for r in top_tg],
    }


def get_scheduled_news() -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM news WHERE status='scheduled' AND scheduled_at IS NOT NULL")
    rows = _fetchall(c)
    conn.close()
    return rows
