# news_fetcher.py
# ─────────────────────────────────────────────────────────────
# Pulls recent headlines for a ticker from Google News RSS.
# No API key required. Used to explain *why* a stock is moving.
# ─────────────────────────────────────────────────────────────

import logging
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

log = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def fetch_news_headlines(symbol: str, max_items: int = 3) -> list[dict]:
    """
    Returns recent news headlines for an NSE ticker, e.g.
      [{"title": "...", "source": "Mint", "url": "...", "published": "Mon, 11 May ..."}]

    Uses Google News RSS — heavily India-biased query to keep results relevant.
    Empty list on any failure (this is best-effort context, not critical).
    """
    query = f'"{symbol}" NSE stock'
    url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    )

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        log.warning(f"News fetch failed for {symbol}: {e}")
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        log.warning(f"News parse failed for {symbol}: {e}")
        return []

    items = []
    for item in root.iter("item"):
        title_el = item.find("title")
        link_el  = item.find("link")
        pub_el   = item.find("pubDate")
        src_el   = item.find("source")

        title = (title_el.text or "").strip() if title_el is not None else ""
        if not title:
            continue

        # Google News titles often end with " - Source Name"
        if " - " in title:
            title, _, source_inline = title.rpartition(" - ")
        else:
            source_inline = ""

        source = (src_el.text or "").strip() if src_el is not None else source_inline

        items.append({
            "title":     title.strip(),
            "source":    source.strip(),
            "url":       (link_el.text or "").strip() if link_el is not None else "",
            "published": (pub_el.text or "").strip() if pub_el is not None else "",
        })

        if len(items) >= max_items:
            break

    return items
