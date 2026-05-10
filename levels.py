# levels.py
# ─────────────────────────────────────────────────────────────
# Calculates Support/Resistance zones, PDH/PDL, EMA
# ─────────────────────────────────────────────────────────────

import pandas as pd
import numpy as np
from config import EMA_PERIOD, SR_ZONE_TOLERANCE, SR_LOOKBACK_DAYS


def calculate_ema(df: pd.DataFrame, period: int = EMA_PERIOD) -> float:
    """Returns the latest EMA value."""
    ema = df["Close"].ewm(span=period, adjust=False).mean()
    return round(ema.iloc[-1], 2)


def find_swing_highs_lows(df: pd.DataFrame, window: int = 5) -> tuple:
    """
    Detects swing highs and swing lows using a rolling window.
    A swing high: candle whose High is the highest in (window) candles on each side.
    A swing low:  candle whose Low  is the lowest  in (window) candles on each side.
    Returns (list of swing high prices, list of swing low prices)
    """
    highs = []
    lows  = []
    data  = df.tail(SR_LOOKBACK_DAYS).reset_index(drop=True)

    for i in range(window, len(data) - window):
        left_highs  = data["High"].iloc[i - window:i]
        right_highs = data["High"].iloc[i + 1:i + window + 1]
        left_lows   = data["Low"].iloc[i - window:i]
        right_lows  = data["Low"].iloc[i + 1:i + window + 1]

        if data["High"].iloc[i] > left_highs.max() and data["High"].iloc[i] > right_highs.max():
            highs.append(round(data["High"].iloc[i], 2))

        if data["Low"].iloc[i] < left_lows.min() and data["Low"].iloc[i] < right_lows.min():
            lows.append(round(data["Low"].iloc[i], 2))

    return highs, lows


def cluster_levels(levels: list, tolerance_pct: float = SR_ZONE_TOLERANCE) -> list:
    """
    Clusters nearby price levels into single zones.
    e.g. [165.0, 165.5, 164.8] → [165.1] (averaged cluster)
    """
    if not levels:
        return []

    levels = sorted(levels)
    clusters = []
    current_cluster = [levels[0]]

    for level in levels[1:]:
        pct_diff = abs(level - current_cluster[-1]) / current_cluster[-1] * 100
        if pct_diff <= tolerance_pct:
            current_cluster.append(level)
        else:
            clusters.append(round(np.mean(current_cluster), 2))
            current_cluster = [level]

    clusters.append(round(np.mean(current_cluster), 2))
    return clusters


def get_key_levels(df: pd.DataFrame, current_price: float) -> dict:
    """
    Returns all key levels for a stock:
    - PDH, PDL (previous day)
    - Support zones (below current price)
    - Resistance zones (above current price)
    - EMA value and price-vs-EMA bias
    - Nearest support and resistance
    """
    # PDH / PDL from previous completed session
    pdh = round(df["High"].iloc[-1], 2)
    pdl = round(df["Low"].iloc[-1], 2)

    # EMA
    ema = calculate_ema(df)
    above_ema = current_price > ema

    # Swing highs/lows
    swing_highs, swing_lows = find_swing_highs_lows(df)

    # Add round numbers near current price as S/R anchors
    price_range = current_price * 0.10  # ±10% range
    round_step  = 50 if current_price > 500 else 10
    round_numbers = [
        round(r, 0)
        for r in np.arange(
            current_price - price_range,
            current_price + price_range,
            round_step
        )
    ]

    all_highs = cluster_levels(swing_highs + [pdh] + round_numbers)
    all_lows  = cluster_levels(swing_lows  + [pdl])

    # Separate into support (below price) and resistance (above price)
    resistances = sorted([l for l in all_highs if l > current_price])
    supports    = sorted([l for l in all_lows  if l < current_price], reverse=True)

    nearest_resistance = resistances[0] if resistances else None
    nearest_support    = supports[0]    if supports    else None

    return {
        "pdh":                round(pdh, 2),
        "pdl":                round(pdl, 2),
        "ema":                ema,
        "above_ema":          above_ema,
        "supports":           supports[:3],     # Top 3 nearest supports
        "resistances":        resistances[:3],  # Top 3 nearest resistances
        "nearest_support":    nearest_support,
        "nearest_resistance": nearest_resistance,
    }


def distance_to_nearest_level(current_price: float, levels: dict) -> float:
    """
    Returns the % distance to the nearest S/R level (support or resistance).
    Used to determine if stock is 'near a key level'.
    """
    candidates = []
    if levels["nearest_support"]:
        candidates.append(abs(current_price - levels["nearest_support"]) / current_price * 100)
    if levels["nearest_resistance"]:
        candidates.append(abs(current_price - levels["nearest_resistance"]) / current_price * 100)
    return min(candidates) if candidates else 999
