# data_fetcher.py
# ─────────────────────────────────────────────────────────────
# Fetches OHLCV data from Yahoo Finance (yfinance) for NSE stocks
# ─────────────────────────────────────────────────────────────

import yfinance as yf
import pandas as pd
import numpy as np
import requests
import logging
from datetime import datetime, timedelta
from config import STOCK_UNIVERSE, EMA_PERIOD, SR_LOOKBACK_DAYS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def fetch_stock_data(symbol: str, days: int = SR_LOOKBACK_DAYS + 10) -> pd.DataFrame | None:
    """
    Fetch daily OHLCV data for a single NSE symbol.
    Returns DataFrame with columns: Open, High, Low, Close, Volume
    Returns None if fetch fails.
    Tries start/end date first, falls back to period="3mo".
    """
    for attempt in ["date_range", "period"]:
        try:
            ticker = yf.Ticker(symbol)

            if attempt == "date_range":
                end   = datetime.today()
                start = end - timedelta(days=days)
                df = ticker.history(start=start, end=end, interval="1d", auto_adjust=True)
            else:
                df = ticker.history(period="3mo", interval="1d", auto_adjust=True)

            if df.empty or len(df) < 20:
                continue

            df.index = pd.to_datetime(df.index).tz_localize(None)
            df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
            return df

        except Exception as e:
            log.warning(f"Attempt '{attempt}' failed for {symbol}: {e}")
            continue

    log.warning(f"All attempts failed for {symbol}")
    return None


def fetch_all_stocks(universe: list = STOCK_UNIVERSE) -> dict:
    """
    Fetch data for all stocks in the universe.
    Returns dict: {symbol: DataFrame}
    """
    log.info(f"Fetching data for {len(universe)} stocks...")
    results = {}
    for symbol in universe:
        df = fetch_stock_data(symbol)
        if df is not None:
            results[symbol] = df
    log.info(f"Successfully fetched {len(results)}/{len(universe)} stocks.")
    return results


def fetch_nifty_futures_change() -> dict:
    """
    Approximates Nifty direction using ^NSEI (Nifty 50 index).
    Returns dict with change_pct and direction label.
    """
    try:
        df = fetch_stock_data("^NSEI", days=5)
        if df is None or len(df) < 2:
            return {"change_pct": 0.0, "direction": "Unknown", "close": 0}

        prev_close = df["Close"].iloc[-2]
        last_close = df["Close"].iloc[-1]
        change_pct = ((last_close - prev_close) / prev_close) * 100

        if change_pct > 0.5:
            direction = "Gap Up 📈"
        elif change_pct < -0.5:
            direction = "Gap Down 📉"
        else:
            direction = "Flat ➡️"

        return {
            "change_pct": round(change_pct, 2),
            "direction":  direction,
            "close":      round(last_close, 2),
        }
    except Exception as e:
        log.warning(f"Failed to fetch Nifty data: {e}")
        return {"change_pct": 0.0, "direction": "Unknown", "close": 0}


def get_prev_day_high_low(df: pd.DataFrame) -> tuple:
    """Returns (PDH, PDL) from the last completed trading day."""
    if len(df) < 2:
        return None, None
    pdh = round(df["High"].iloc[-1], 2)
    pdl = round(df["Low"].iloc[-1], 2)
    return pdh, pdl


def clean_symbol(symbol: str) -> str:
    """Strip .NS suffix for display."""
    return symbol.replace(".NS", "")
