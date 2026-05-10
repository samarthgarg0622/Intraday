# screener.py
# ─────────────────────────────────────────────────────────────
# Runs the 4-filter screening logic on the universe
# Returns ranked shortlist with bias and levels
# ─────────────────────────────────────────────────────────────

import pandas as pd
import numpy as np
import logging
from data_fetcher import fetch_all_stocks, clean_symbol
from levels import get_key_levels, distance_to_nearest_level
from config import (
    MIN_PRICE, MAX_PRICE,
    MIN_VOLUME_RATIO, MIN_PRICE_MOVE_PCT,
    NEAR_LEVEL_PCT, MAX_WATCHLIST_SIZE,
    STOCK_UNIVERSE, EMA_PERIOD
)

log = logging.getLogger(__name__)


def calculate_volume_ratio(df: pd.DataFrame) -> float:
    """Today's volume vs 20-day average volume."""
    if len(df) < 21:
        return 0.0
    avg_volume   = df["Volume"].iloc[-21:-1].mean()  # 20-day avg excluding today
    today_volume = df["Volume"].iloc[-1]
    if avg_volume == 0:
        return 0.0
    return round(today_volume / avg_volume, 2)


def calculate_day_change_pct(df: pd.DataFrame) -> float:
    """% change from previous close to today's close."""
    if len(df) < 2:
        return 0.0
    prev  = df["Close"].iloc[-2]
    today = df["Close"].iloc[-1]
    return round(((today - prev) / prev) * 100, 2)


def determine_bias(df: pd.DataFrame, levels: dict, change_pct: float) -> str:
    """
    Determines LONG / SHORT / NEUTRAL bias based on:
    - Price vs EMA
    - Direction of today's move
    - Position relative to PDH/PDL
    """
    price       = df["Close"].iloc[-1]
    above_ema   = levels["above_ema"]
    near_res    = levels["nearest_resistance"]
    near_sup    = levels["nearest_support"]

    # Proximity to resistance vs support
    dist_to_res = abs(price - near_res) / price * 100 if near_res else 999
    dist_to_sup = abs(price - near_sup) / price * 100 if near_sup else 999

    # Score for long/short
    long_score  = 0
    short_score = 0

    if above_ema:          long_score  += 2
    else:                  short_score += 2

    if change_pct > 0:     long_score  += 1
    else:                  short_score += 1

    if dist_to_res < dist_to_sup:
        # Closer to resistance — potential breakout (long) or rejection (short)
        if above_ema:      long_score  += 1   # Trending up → breakout likely
        else:              short_score += 1   # Trending down → rejection likely
    else:
        # Closer to support
        if above_ema:      long_score  += 1
        else:              short_score += 1

    if long_score > short_score:
        return "LONG"
    elif short_score > long_score:
        return "SHORT"
    else:
        return "NEUTRAL"


def determine_setup_type(df: pd.DataFrame, levels: dict, bias: str) -> str:
    """Returns a human-readable setup description."""
    price   = df["Close"].iloc[-1]
    pdh     = levels["pdh"]
    pdl     = levels["pdl"]
    near_r  = levels["nearest_resistance"]
    near_s  = levels["nearest_support"]

    if near_r and abs(price - near_r) / price * 100 < NEAR_LEVEL_PCT:
        if bias == "LONG":
            return "🔥 Near resistance → watch for breakout above"
        else:
            return "⚠️ Near resistance → watch for rejection short"

    if near_s and abs(price - near_s) / price * 100 < NEAR_LEVEL_PCT:
        if bias == "SHORT":
            return "🔥 Near support → watch for breakdown below"
        else:
            return "⚠️ Near support → watch for bounce long"

    if price > pdh * 0.995:
        return "📈 Near PDH — breakout watch"
    if price < pdl * 1.005:
        return "📉 Near PDL — breakdown watch"

    return "📊 Momentum play — trend continuation"


def score_stock(volume_ratio: float, change_pct: float,
                near_level: bool, above_ema: bool) -> int:
    """Scores a stock 0–4 based on how many filters it passes."""
    score = 0
    if volume_ratio >= MIN_VOLUME_RATIO:         score += 1
    if abs(change_pct) >= MIN_PRICE_MOVE_PCT:    score += 1
    if near_level:                               score += 1
    if above_ema is not None:                    score += 1  # Always passes if EMA exists
    return score


def run_screener(stock_data: dict = None) -> list:
    """
    Main screening function.
    Returns a sorted list of dicts with stock info + levels for top candidates.
    """
    if stock_data is None:
        stock_data = fetch_all_stocks()

    results = []

    for symbol, df in stock_data.items():
        try:
            if len(df) < 25:
                continue

            price = df["Close"].iloc[-1]

            # Price range filter
            if not (MIN_PRICE <= price <= MAX_PRICE):
                continue

            volume_ratio = calculate_volume_ratio(df)
            change_pct   = calculate_day_change_pct(df)
            levels       = get_key_levels(df, price)
            dist_to_lvl  = distance_to_nearest_level(price, levels)
            near_level   = dist_to_lvl <= NEAR_LEVEL_PCT

            # Must pass at least 2 of 3 core filters
            passes_volume = volume_ratio >= MIN_VOLUME_RATIO
            passes_move   = abs(change_pct) >= MIN_PRICE_MOVE_PCT

            if not (passes_volume or passes_move):
                continue
            if not (passes_volume and passes_move) and not near_level:
                continue

            bias       = determine_bias(df, levels, change_pct)
            setup_type = determine_setup_type(df, levels, bias)
            score      = score_stock(volume_ratio, change_pct, near_level, levels["above_ema"])

            results.append({
                "symbol":       symbol,
                "display":      clean_symbol(symbol),
                "price":        round(price, 2),
                "change_pct":   change_pct,
                "volume_ratio": volume_ratio,
                "near_level":   near_level,
                "dist_to_lvl":  round(dist_to_lvl, 2),
                "bias":         bias,
                "setup":        setup_type,
                "score":        score,
                "levels":       levels,
                "df":           df,
            })

        except Exception as e:
            log.warning(f"Error screening {symbol}: {e}")
            continue

    # Sort by score descending, then by volume ratio
    results.sort(key=lambda x: (x["score"], x["volume_ratio"]), reverse=True)

    # Return top N
    return results[:MAX_WATCHLIST_SIZE]
