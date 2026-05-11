# volume_gainers.py
# ─────────────────────────────────────────────────────────────
# Crawls NSE's live volume-gainers feed.
# NSE blocks plain requests, so we bootstrap cookies via the
# public landing page first, then hit the JSON API.
# ─────────────────────────────────────────────────────────────

import logging
import requests
from config import (
    MOMENTUM_MIN_VOLUME_LAKHS,
    MOMENTUM_MIN_VALUE_CR,
    MOMENTUM_MIN_VOL_RATIO,
    MOMENTUM_TOP_N,
)

log = logging.getLogger(__name__)

NSE_BASE        = "https://www.nseindia.com"
NSE_VOL_GAINERS = f"{NSE_BASE}/api/live-analysis-volume-gainers"
NSE_REFERER     = f"{NSE_BASE}/market-data/volume-gainers"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         NSE_REFERER,
}


def _nse_session() -> requests.Session:
    """Bootstrap a session with NSE cookies. Required before any API call."""
    s = requests.Session()
    s.headers.update(_HEADERS)
    # Two warm-up hits: landing page sets baseline cookies,
    # the referer page sets API-specific cookies.
    s.get(NSE_BASE, timeout=10)
    s.get(NSE_REFERER, timeout=10)
    return s


def fetch_nse_volume_gainers() -> list[dict]:
    """
    Returns raw rows from NSE volume gainers API.
    Each row roughly looks like:
      symbol, ltp, netPrice (% change), todaysVolume, weekAvgVolume,
      volumeGainTimes, todaysTurnover (in lakhs)
    Field names occasionally shift — callers should use .get() everywhere.
    """
    try:
        session = _nse_session()
        resp = session.get(NSE_VOL_GAINERS, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        rows = payload.get("data") or payload.get("VOLUME_GAINERS_DATA") or []
        log.info(f"NSE volume gainers: fetched {len(rows)} rows")
        return rows
    except Exception as e:
        log.error(f"NSE volume gainers fetch failed: {e}")
        return []


def _row_volume_lakhs(row: dict) -> float:
    """Today's traded quantity, in lakhs (1 lakh = 100,000 shares)."""
    qty = row.get("volume") or row.get("todaysVolume") or row.get("totalTradedVolume") or 0
    try:
        return float(qty) / 1e5
    except (TypeError, ValueError):
        return 0.0


def _row_value_cr(row: dict) -> float:
    """Today's traded value, in ₹ crore. NSE turnover is reported in lakhs."""
    turnover_lakhs = (
        row.get("turnover")
        or row.get("todaysTurnover")
        or row.get("totalTradedValue")
        or 0
    )
    try:
        return float(turnover_lakhs) / 100.0   # 100 lakh = 1 crore
    except (TypeError, ValueError):
        return 0.0


def _row_vol_ratio(row: dict) -> float:
    """Today's volume / weekly average volume."""
    for key in ("week1volChange", "volumeGainTimes"):
        v = row.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    today = row.get("volume") or row.get("todaysVolume") or 0
    avg   = row.get("week1AvgVolume") or row.get("weekAvgVolume") or 0
    try:
        today, avg = float(today), float(avg)
        return round(today / avg, 2) if avg else 0.0
    except (TypeError, ValueError):
        return 0.0


def _row_change_pct(row: dict) -> float:
    for key in ("pChange", "netPrice", "perChange", "change_pct"):
        v = row.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return 0.0


def _row_ltp(row: dict) -> float:
    for key in ("ltp", "lastPrice", "last"):
        v = row.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return 0.0


def filter_top_gainers(rows: list[dict]) -> list[dict]:
    """
    Keep rows that clear the liquidity bar (volume + traded value) and a
    minimum volume-vs-average ratio. Return the top N by volume ratio.
    Normalized dicts are returned (not raw NSE rows).
    """
    cleaned = []
    for row in rows:
        symbol = (row.get("symbol") or "").upper().strip()
        if not symbol:
            continue

        volume_l = _row_volume_lakhs(row)
        value_cr = _row_value_cr(row)
        vol_x    = _row_vol_ratio(row)
        change   = _row_change_pct(row)
        ltp      = _row_ltp(row)

        if volume_l < MOMENTUM_MIN_VOLUME_LAKHS: continue
        if value_cr < MOMENTUM_MIN_VALUE_CR:     continue
        if vol_x    < MOMENTUM_MIN_VOL_RATIO:    continue
        if ltp <= 0:                             continue

        cleaned.append({
            "symbol":     symbol,
            "yf_symbol":  f"{symbol}.NS",
            "ltp":        round(ltp, 2),
            "change_pct": round(change, 2),
            "volume_l":   round(volume_l, 2),
            "value_cr":   round(value_cr, 2),
            "vol_x":      round(vol_x, 2),
        })

    cleaned.sort(key=lambda x: x["vol_x"], reverse=True)
    return cleaned[:MOMENTUM_TOP_N]
