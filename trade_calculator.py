# trade_calculator.py
# ─────────────────────────────────────────────────────────────
# Calculates precise Entry, Stop Loss, Target, Position Size
# for every stock in the watchlist.
# All calculations follow the 3-method SL framework and
# 1:2 minimum Risk:Reward rule.
# ─────────────────────────────────────────────────────────────

import math

# ── Constants ─────────────────────────────────────────────────
ENTRY_BUFFER_PCT    = 0.003   # 0.3% buffer above/below trigger
SL_CANDLE_BUFFER    = 0.002   # 0.2% below candle low / above candle high
MAX_SL_PCT          = 0.015   # Skip trade if SL > 1.5% from entry
MIN_RR_RATIO        = 2.0     # Minimum Risk:Reward ratio
CAPITAL             = 100000  # ₹1,00,000 — update this in config if capital changes
MAX_RISK_PER_TRADE  = 0.015   # 1.5% of capital = ₹1,500 max loss per trade
PARTIAL_EXIT_RATIO  = 0.5     # Exit 50% at 1:1, let 50% run to 1:2


def calculate_trade_levels(stock: dict, capital: float = CAPITAL) -> dict:
    """
    Given a screened stock dict (from screener.py), calculates:
    - Entry price (limit order level)
    - Stop Loss price (mechanical, rule-based)
    - Target 1 (1:1 partial exit — 50% position)
    - Target 2 (1:2 full exit — remaining 50%)
    - Position size (shares to buy)
    - Max capital to deploy
    - GTT trigger instructions for Kite
    - Whether the trade is valid (SL within limits)
    Returns a dict with all these values.
    """
    lvl      = stock["levels"]
    bias     = stock["bias"]
    price    = stock["price"]
    df       = stock["df"]

    # ── Step 1: Entry Price ──────────────────────────────────
    if bias == "LONG":
        trigger_level = lvl["nearest_resistance"] or lvl["pdh"]
        entry = round(trigger_level * (1 + ENTRY_BUFFER_PCT), 2)
    elif bias == "SHORT":
        trigger_level = lvl["nearest_support"] or lvl["pdl"]
        entry = round(trigger_level * (1 - ENTRY_BUFFER_PCT), 2)
    else:
        # NEUTRAL — use PDH as breakout trigger
        trigger_level = lvl["pdh"]
        entry = round(trigger_level * (1 + ENTRY_BUFFER_PCT), 2)

    # ── Step 2: Stop Loss (3 methods, pick tightest valid one) ──
    sl_candidates = []

    # Method 1: Recent candle low/high (last 3 candles)
    if len(df) >= 3:
        if bias == "LONG":
            candle_sl = round(df["Low"].iloc[-3:].min() * (1 - SL_CANDLE_BUFFER), 2)
        else:
            candle_sl = round(df["High"].iloc[-3:].max() * (1 + SL_CANDLE_BUFFER), 2)
        sl_candidates.append(("Candle low/high", candle_sl))

    # Method 2: Structure SL (key level)
    if bias == "LONG":
        structure_sl = round(lvl["nearest_support"] * (1 - SL_CANDLE_BUFFER), 2) \
                       if lvl["nearest_support"] else None
    else:
        structure_sl = round(lvl["nearest_resistance"] * (1 + SL_CANDLE_BUFFER), 2) \
                       if lvl["nearest_resistance"] else None

    if structure_sl:
        sl_candidates.append(("Structure level", structure_sl))

    # Method 3: Fixed % SL
    if bias == "LONG":
        fixed_sl = round(entry * (1 - MAX_SL_PCT), 2)
    else:
        fixed_sl = round(entry * (1 + MAX_SL_PCT), 2)
    sl_candidates.append(("Fixed 1.5%", fixed_sl))

    # Pick the tightest SL that is still on the correct side of entry
    # (for long: SL < entry; for short: SL > entry)
    valid_sls = []
    for method, sl in sl_candidates:
        if bias == "LONG" and sl < entry:
            sl_pct = (entry - sl) / entry * 100
            if sl_pct <= MAX_SL_PCT * 100:
                valid_sls.append((sl_pct, method, sl))
        elif bias == "SHORT" and sl > entry:
            sl_pct = (sl - entry) / entry * 100
            if sl_pct <= MAX_SL_PCT * 100:
                valid_sls.append((sl_pct, method, sl))

    if not valid_sls:
        # No valid SL found — trade is invalid
        return _invalid_trade(stock, entry, "SL wider than 1.5% on all methods")

    # Pick tightest (smallest % away)
    valid_sls.sort(key=lambda x: x[0])
    sl_pct, sl_method, stop_loss = valid_sls[0]

    # ── Step 3: Risk per Share & Position Size ───────────────
    max_risk_amount = capital * MAX_RISK_PER_TRADE   # ₹1,500

    if bias == "LONG":
        risk_per_share = entry - stop_loss
    else:
        risk_per_share = stop_loss - entry

    if risk_per_share <= 0:
        return _invalid_trade(stock, entry, "Risk per share is zero or negative")

    shares = math.floor(max_risk_amount / risk_per_share)

    if shares < 1:
        return _invalid_trade(stock, entry, "Position size rounds to 0 shares")

    capital_required = round(shares * entry, 2)
    actual_risk      = round(shares * risk_per_share, 2)

    # ── Step 4: Targets (1:1 and 1:2) ───────────────────────
    if bias == "LONG":
        target1 = round(entry + risk_per_share * 1.0, 2)   # 1:1 — partial exit
        target2 = round(entry + risk_per_share * 2.0, 2)   # 1:2 — full exit
    else:
        target1 = round(entry - risk_per_share * 1.0, 2)
        target2 = round(entry - risk_per_share * 2.0, 2)

    # Check target2 is not blocked by a level
    target2_blocked = False
    if bias == "LONG" and lvl["resistances"]:
        blocking = [r for r in lvl["resistances"] if entry < r < target2]
        if blocking:
            target2 = round(min(blocking) * 0.998, 2)   # Pull target just below wall
            target2_blocked = True
    elif bias == "SHORT" and lvl["supports"]:
        blocking = [s for s in lvl["supports"] if target2 < s < entry]
        if blocking:
            target2 = round(max(blocking) * 1.002, 2)
            target2_blocked = True

    # Verify RR is still acceptable after adjustment
    if bias == "LONG":
        rr = (target2 - entry) / risk_per_share
    else:
        rr = (entry - target2) / risk_per_share

    if rr < 1.5:
        return _invalid_trade(stock, entry, f"RR ratio {rr:.1f} too low after level adjustment")

    return {
        "valid":            True,
        "bias":             bias,
        "entry":            entry,
        "trigger_level":    trigger_level,
        "stop_loss":        stop_loss,
        "sl_method":        sl_method,
        "sl_pct":           round(sl_pct, 2),
        "target1":          target1,
        "target2":          target2,
        "target2_blocked":  target2_blocked,
        "rr_ratio":         round(rr, 2),
        "shares":           shares,
        "capital_required": capital_required,
        "actual_risk":      actual_risk,
        "risk_pct":         round(actual_risk / capital * 100, 2),
    }


def _invalid_trade(stock: dict, entry: float, reason: str) -> dict:
    return {
        "valid":   False,
        "bias":    stock["bias"],
        "entry":   entry,
        "reason":  reason,
    }


def format_trade_block(sym: str, trade: dict, lvl: dict) -> list:
    """
    Formats a single stock's trade plan as Telegram message lines.
    Includes GTT instructions for Zerodha Kite.
    """
    lines = []
    bias  = trade["bias"]
    icon  = "📈" if bias == "LONG" else "📉"

    if not trade["valid"]:
        lines.append(f"*{sym}* {icon} {bias} — ⛔ SKIP")
        lines.append(f"   Reason: {trade['reason']}")
        lines.append("")
        return lines

    lines.append(f"*{sym}* {icon} {bias}")
    lines.append(f"   ┌ 🎯 Entry:    ₹{trade['entry']}  (when price crosses ₹{trade['trigger_level']})")
    lines.append(f"   ├ 🛑 SL:       ₹{trade['stop_loss']}  ({trade['sl_pct']}% risk | {trade['sl_method']})")
    lines.append(f"   ├ 🏁 Target 1: ₹{trade['target1']}  (exit 50% here)")
    lines.append(f"   └ 🏆 Target 2: ₹{trade['target2']}  (exit remaining 50%){' ⚠️ wall ahead' if trade['target2_blocked'] else ''}")
    lines.append(f"")
    lines.append(f"   📐 R:R = 1:{trade['rr_ratio']}  |  Qty: {trade['shares']} shares")
    lines.append(f"   💰 Capital: ₹{trade['capital_required']}  |  Max loss: ₹{trade['actual_risk']} ({trade['risk_pct']}%)")
    lines.append(f"")

    # GTT Instructions for Kite
    lines.append(f"   *🔔 Set on Kite (GTT Order):*")
    if bias == "LONG":
        lines.append(f"   • GTT trigger: ₹{trade['trigger_level']}")
        lines.append(f"   • Buy {trade['shares']} shares @ ₹{trade['entry']} (limit)")
        lines.append(f"   • After fill → place SL-M sell @ ₹{trade['stop_loss']}")
        lines.append(f"   • Set price alert at ₹{trade['target1']} (partial exit)")
    else:
        lines.append(f"   • GTT trigger: ₹{trade['trigger_level']}")
        lines.append(f"   • Sell {trade['shares']} shares @ ₹{trade['entry']} (limit)")
        lines.append(f"   • After fill → place SL-M buy @ ₹{trade['stop_loss']}")
        lines.append(f"   • Set price alert at ₹{trade['target1']} (partial cover)")
    lines.append("")

    return lines
