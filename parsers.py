"""
Парсеры новостных сайтов
"""
import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


async def fetch(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                return await resp.text(errors="replace")
    except Exception as e:
        logger.warning(f"fetch error {url}: {e}")
    return None


def extract_og_image(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """Извлекаем og:image или первую картинку из статьи"""
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        img = og["content"]
        return img if img.startswith("http") else urljoin(base_url, img)
    # Первая большая картинка
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src and ("upload" in src or "photo" in src or "image" in src or "img" in src):
            return src if src.startswith("http") else urljoin(base_url, src)
    return None


# ─────────────────────────────────────────
# Парсер: gomel.today
# ─────────────────────────────────────────
async def parse_gomel_today(session: aiohttp.ClientSession) -> List[Dict]:
    base = "https://gomel.today"
    html = await fetch(session, base)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for a in soup.select("a.news-item, article a, .post-title a, h2 a, h3 a")[:20]:
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if not href or len(title) < 10:
            continue
        url = href if href.startswith("http") else urljoin(base, href)
        # Загружаем статью для картинки и текста
        art_html = await fetch(session, url)
        image_url, text = None, title
        if art_html:
            asoup = BeautifulSoup(art_html, "html.parser")
            image_url = extract_og_image(asoup, url)
            content = asoup.select_one(".article-content, .entry-content, .content, article p")
            if content:
                text = content.get_text(" ", strip=True)[:1000]
        results.append({
            "source_name": "gomel.today",
            "source_type": "site",
            "title": title,
            "text": text,
            "url": url,
            "image_url": image_url,
        })
    return results


# ─────────────────────────────────────────
# Парсер: nashgomel.by (RSS)
# ─────────────────────────────────────────
async def parse_nashgomel(session: aiohttp.ClientSession) -> List[Dict]:
    rss_url = "https://nashgomel.by/feed/"
    html = await fetch(session, rss_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "xml")
    results = []
    for item in soup.find_all("item")[:15]:
        title = item.find("title")
        link = item.find("link")
        desc = item.find("description")
        if not title or not link:
            continue
        url = link.get_text(strip=True)
        text = BeautifulSoup(desc.get_text() if desc else "", "html.parser").get_text(strip=True)[:800]
        # Картинка из enclosure или content
        image_url = None
        enc = item.find("enclosure")
        if enc:
            image_url = enc.get("url")
        if not image_url:
            media = item.find("media:content")
            if media:
                image_url = media.get("url")
        results.append({
            "source_name": "nashgomel.by",
            "source_type": "site",
            "title": title.get_text(strip=True),
            "text": text,
            "url": url,
            "image_url": image_url,
        })
    return results


# ─────────────────────────────────────────
# Парсер: newsgomel.by (RSS)
# ─────────────────────────────────────────
async def parse_newsgomel(session: aiohttp.ClientSession) -> List[Dict]:
    rss_url = "https://newsgomel.by/feed/"
    html = await fetch(session, rss_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "xml")
    results = []
    for item in soup.find_all("item")[:15]:
        title = item.find("title")
        link = item.find("link")
        desc = item.find("description")
        if not title or not link:
            continue
        url = link.get_text(strip=True)
        text = BeautifulSoup(desc.get_text() if desc else "", "html.parser").get_text(strip=True)[:800]
        image_url = None
        enc = item.find("enclosure")
        if enc:
            image_url = enc.get("url")
        results.append({
            "source_name": "newsgomel.by",
            "source_type": "site",
            "title": title.get_text(strip=True),
            "text": text,
            "url": url,
            "image_url": image_url,
        })
    return results


# ─────────────────────────────────────────
# Парсер: gp.by (RSS)
# ─────────────────────────────────────────
async def parse_gp(session: aiohttp.ClientSession) -> List[Dict]:
    rss_url = "https://gp.by/rss.xml"
    html = await fetch(session, rss_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "xml")
    results = []
    for item in soup.find_all("item")[:15]:
        title = item.find("title")
        link = item.find("link")
        desc = item.find("description")
        if not title or not link:
            continue
        results.append({
            "source_name": "gp.by",
            "source_type": "site",
            "title": title.get_text(strip=True),
            "text": BeautifulSoup(desc.get_text() if desc else "", "html.parser").get_text(strip=True)[:800],
            "url": link.get_text(strip=True),
            "image_url": None,
        })
    return results


# ─────────────────────────────────────────
# Парсер: onliner.by (RSS + фильтр Гомель)
# ─────────────────────────────────────────
async def parse_onliner(session: aiohttp.ClientSession, keyword: str = "гомел") -> List[Dict]:
    rss_url = "https://www.onliner.by/feed"
    html = await fetch(session, rss_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "xml")
    results = []
    for item in soup.find_all("item")[:30]:
        title = item.find("title")
        link = item.find("link")
        desc = item.find("description")
        if not title or not link:
            continue
        title_text = title.get_text(strip=True)
        desc_text = BeautifulSoup(desc.get_text() if desc else "", "html.parser").get_text(strip=True)
        if keyword.lower() not in title_text.lower() and keyword.lower() not in desc_text.lower():
            continue
        results.append({
            "source_name": "onliner.by",
            "source_type": "site",
            "title": title_text,
            "text": desc_text[:800],
            "url": link.get_text(strip=True),
            "image_url": None,
        })
    return results


# ─────────────────────────────────────────
# Парсер: sb.by
# ─────────────────────────────────────────
async def parse_sb(session: aiohttp.ClientSession, keyword: str = "гомел") -> List[Dict]:
    # Поиск по тегу Гомель
    url = "https://www.sb.by/articles/gomel/"
    html = await fetch(session, url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for a in soup.select("a.article__title, .news-list a, h2 a, h3 a")[:15]:
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if not href or len(title) < 10:
            continue
        art_url = href if href.startswith("http") else urljoin("https://www.sb.by", href)
        image_url = None
        art_html = await fetch(session, art_url)
        if art_html:
            asoup = BeautifulSoup(art_html, "html.parser")
            image_url = extract_og_image(asoup, art_url)
        results.append({
            "source_name": "sb.by",
            "source_type": "site",
            "title": title,
            "text": title,
            "url": art_url,
            "image_url": image_url,
        })
    return results


# ─────────────────────────────────────────
# Парсер: belta.by (RSS + фильтр)
# ─────────────────────────────────────────
async def parse_belta(session: aiohttp.ClientSession, keyword: str = "гомел") -> List[Dict]:
    rss_url = "https://belta.by/rss/all"
    html = await fetch(session, rss_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "xml")
    results = []
    for item in soup.find_all("item")[:30]:
        title = item.find("title")
        link = item.find("link")
        desc = item.find("description")
        if not title or not link:
            continue
        title_text = title.get_text(strip=True)
        desc_text = BeautifulSoup(desc.get_text() if desc else "", "html.parser").get_text(strip=True)
        if keyword.lower() not in title_text.lower() and keyword.lower() not in desc_text.lower():
            continue
        results.append({
            "source_name": "belta.by",
            "source_type": "site",
            "title": title_text,
            "text": desc_text[:800],
            "url": link.get_text(strip=True),
            "image_url": None,
        })
    return results


# ─────────────────────────────────────────
# Главная функция: парсим все сайты
# ─────────────────────────────────────────
PARSERS = {
    "gomel.today":  parse_gomel_today,
    "nashgomel.by": parse_nashgomel,
    "newsgomel.by": parse_newsgomel,
    "gp.by":        parse_gp,
    "onliner.by":   parse_onliner,
    "sb.by":        parse_sb,
    "belta.by":     parse_belta,
}


async def fetch_all_sites(enabled_sites: List[dict]) -> List[Dict]:
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = []
        names = []
        for site in enabled_sites:
            if not site.get("enabled", True):
                continue
            name = site["name"]
            if name in PARSERS:
                tasks.append(PARSERS[name](session))
                names.append(name)
        if not tasks:
            return []
        fetched = await asyncio.gather(*tasks, return_exceptions=True)
        for name, res in zip(names, fetched):
            if isinstance(res, Exception):
                logger.error(f"Parser error {name}: {res}")
            elif res:
                results.extend(res)
    return results
