# alert_formatter.py
# ─────────────────────────────────────────────────────────────
# Formats the night brief and morning brief as Telegram messages
# Includes Entry, SL, Target, Position Size, GTT instructions
# ─────────────────────────────────────────────────────────────

from datetime import datetime
import pytz
from trade_calculator import calculate_trade_levels, format_trade_block

IST = pytz.timezone("Asia/Kolkata")


def _ist_now() -> datetime:
    return datetime.now(IST)


def _date_str() -> str:
    return _ist_now().strftime("%a, %d %b %Y")


def format_night_brief(watchlist: list) -> str:
    """
    Formats the full nightly watchlist message for Telegram.
    Includes: Entry, SL, Target 1, Target 2, Position Size, GTT steps.
    """
    if not watchlist:
        return (
            f"🌙 *NIGHT BRIEF — {_date_str()}*\n\n"
            "No strong setups found today.\n"
            "Market may be consolidating — consider sitting out tomorrow.\n\n"
            "_Stay patient. Capital protection first._"
        )

    lines = [f"🌙 *NIGHT BRIEF — {_date_str()}*\n"]
    lines.append(f"📋 *WATCHLIST — {len(watchlist)} setup(s)*")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━\n")

    valid_count = 0
    skip_count  = 0

    for i, stock in enumerate(watchlist, 1):
        sym   = stock["display"]
        price = stock["price"]
        chg   = stock["change_pct"]
        vol   = stock["volume_ratio"]
        lvl   = stock["levels"]
        setup = stock["setup"]

        chg_icon = "🟢" if chg >= 0 else "🔴"

        lines.append(f"*{i}. {sym}*")
        lines.append(f"   Close: ₹{price}  {chg_icon} {chg:+.2f}%  |  Vol: {vol}x avg")
        lines.append(f"   PDH: ₹{lvl['pdh']}  PDL: ₹{lvl['pdl']}  EMA20: ₹{lvl['ema']} ({'above ✅' if lvl['above_ema'] else 'below ⚠️'})")
        lines.append(f"   {setup}")
        lines.append("")

        trade = calculate_trade_levels(stock)
        trade_lines = format_trade_block(sym, trade, lvl)
        lines.extend(trade_lines)

        if trade["valid"]:
            valid_count += 1
        else:
            skip_count += 1

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"*Summary:* {valid_count} tradeable  |  {skip_count} skipped")
    lines.append("")
    lines.append("*Rules for tomorrow:*")
    lines.append("• Wait for 9:30 AM — no trades before this")
    lines.append("• Entry ONLY after 5-min candle confirms the level")
    lines.append("• Place SL order immediately after entry fills")
    lines.append("• Exit 50% at Target 1, move SL to breakeven")
    lines.append("• Close ALL positions by 3:20 PM")
    lines.append("• Daily max loss ₹2,000 — stop trading if hit")
    lines.append("\n_Good rest = good decisions. Sleep well._ 🌙")

    return "\n".join(lines)


def format_morning_brief(watchlist: list, nifty: dict, comparison: dict = None) -> str:
    """
    Formats the morning alert (8:45 AM) with gap analysis,
    night-vs-morning comparison, and final actionable trade plan.
    """
    date_str    = _date_str()
    chg         = nifty.get("change_pct", 0)
    direction   = nifty.get("direction", "Unknown")
    nifty_close = nifty.get("close", 0)

    lines = [f"☀️ *MORNING BRIEF — {date_str}*\n"]

    lines.append(f"🇮🇳 *Nifty 50:* ₹{nifty_close}  {direction}  ({chg:+.2f}%)")

    if abs(chg) > 1.0:
        lines.append("⚠️ _High volatility open — reduce qty by 50% or skip_")
    elif abs(chg) < 0.3:
        lines.append("ℹ️ _Flat open — wait for direction to establish after 9:30 AM_")

    lines.append("")

    # ── Night vs Morning Comparison ───────────────────────────
    if comparison:
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("*🔍 OVERNIGHT CHECK vs LAST NIGHT*\n")

        if comparison["still_valid"]:
            lines.append(f"✅ *Unchanged:* {', '.join(comparison['still_valid'])}")

        if comparison["levels_changed"]:
            lines.append("📐 *Levels shifted (review before trading):*")
            for s in comparison["levels_changed"]:
                lines.append(f"   {s['display']}:")
                for c in s["changes"]:
                    lines.append(f"     • {c}")

        if comparison["bias_changed"]:
            lines.append("🔄 *Bias flipped overnight (trade with caution):*")
            for s in comparison["bias_changed"]:
                lines.append(f"   {s['display']}: {s['was']} → {s['now']}")

        if comparison["dropped"]:
            lines.append(f"❌ *Dropped from list:* {', '.join(comparison['dropped'])}")
            lines.append("   _These no longer meet screening criteria — skip today_")

        if comparison["new_additions"]:
            lines.append(f"🆕 *New additions:* {', '.join(comparison['new_additions'])}")
            lines.append("   _Not in last night's brief — smaller position size recommended_")

        if not any([comparison["levels_changed"], comparison["bias_changed"],
                    comparison["dropped"], comparison["new_additions"]]):
            lines.append("✅ _All setups confirmed overnight. No changes._")

        lines.append("")

    # ── Trade Plans ───────────────────────────────────────────
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")

    if not watchlist:
        lines.append("No stocks qualify today. Stand down.")
        return "\n".join(lines)

    nifty_bullish = chg >= 0
    lines.append("*TODAY'S TRADE PLANS*\n")

    for stock in watchlist:
        sym  = stock["display"]
        bias = stock["bias"]

        aligned = (bias == "LONG" and nifty_bullish) or \
                  (bias == "SHORT" and not nifty_bullish) or \
                  bias == "NEUTRAL"

        status_tag = "✅ GO" if aligned else "⚠️ COUNTER-TREND"

        lines.append(f"*{sym}* — {status_tag}")

        trade = calculate_trade_levels(stock)
        if trade["valid"]:
            lines.append(f"   Entry: ₹{trade['entry']}  |  SL: ₹{trade['stop_loss']}")
            lines.append(f"   T1: ₹{trade['target1']} (50% exit)  |  T2: ₹{trade['target2']}")
            lines.append(f"   Qty: {trade['shares']} shares  |  Risk: ₹{trade['actual_risk']}")
            if not aligned:
                lines.append("   _Skip or halve qty — counter to Nifty direction_")
        else:
            lines.append(f"   ⛔ Skip — {trade['reason']}")

        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("*Pre-Market Checklist:*")
    lines.append("☐  9:15–9:30 AM: observe only, no orders")
    lines.append("☐  9:30 AM onwards: set GTT only if setup is still valid on chart")
    lines.append("☐  SL confirmed (max ₹1,500 per trade)")
    lines.append("☐  3:15 PM exit alarm set on phone")
    lines.append("\n_Trade what the market gives. Not what you want._ 📊")

    return "\n".join(lines)


def format_error_alert(job_name: str, error: str) -> str:
    return (
        f"⚠️ *TRADER ASSISTANT ERROR*\n\n"
        f"Job: `{job_name}`\n"
        f"Time: {_ist_now().strftime('%H:%M IST')}\n"
        f"Error: `{error}`\n\n"
        f"_Check logs on Railway._"
    )
