# momentum_job.py
# ─────────────────────────────────────────────────────────────
# On-demand momentum scan.
#   1. Crawls NSE volume gainers
#   2. Filters for good volume + good traded value
#   3. For each survivor: fetches OHLCV, computes levels,
#      derives a directional bias from today's move, sizes a trade
#   4. Pulls news headlines so you can see *why* it's moving
#   5. Posts a Telegram message with the plan(s)
# ─────────────────────────────────────────────────────────────

import logging
from datetime import datetime
import pytz

from volume_gainers import fetch_nse_volume_gainers, filter_top_gainers
from news_fetcher   import fetch_news_headlines
from data_fetcher   import fetch_stock_data, clean_symbol
from levels         import get_key_levels
from trade_calculator import calculate_trade_levels
from telegram_sender  import send_message
from alert_formatter  import format_error_alert

log = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")


def _bias_from_change(change_pct: float) -> str:
    if change_pct >  0.2: return "LONG"
    if change_pct < -0.2: return "SHORT"
    return "NEUTRAL"


def _build_stock_dict(gainer: dict) -> dict | None:
    """
    Pull OHLCV for a gainer and assemble the dict shape that
    trade_calculator expects. Returns None if data is unavailable.
    """
    df = fetch_stock_data(gainer["yf_symbol"])
    if df is None or len(df) < 25:
        log.warning(f"Skipping {gainer['symbol']} — insufficient OHLCV")
        return None

    price  = float(df["Close"].iloc[-1])
    levels = get_key_levels(df, price)
    bias   = _bias_from_change(gainer["change_pct"])

    return {
        "symbol":       gainer["yf_symbol"],
        "display":      clean_symbol(gainer["yf_symbol"]),
        "price":        round(price, 2),
        "change_pct":   gainer["change_pct"],
        "volume_ratio": gainer["vol_x"],
        "bias":         bias,
        "levels":       levels,
        "df":           df,
    }


def _format_news(headlines: list[dict]) -> list[str]:
    if not headlines:
        return ["   _No fresh headlines found._"]
    lines = []
    for h in headlines:
        src = f" ({h['source']})" if h["source"] else ""
        lines.append(f"   • {h['title']}{src}")
    return lines


def _format_momentum_brief(plans: list[dict]) -> str:
    now = datetime.now(IST).strftime("%a, %d %b %Y · %H:%M IST")
    lines = [f"⚡ *MOMENTUM SCAN — {now}*\n"]

    if not plans:
        lines.append("No volume gainers cleared the liquidity filter.")
        lines.append("_Either the market hasn't moved, or NSE feed is empty right now._")
        return "\n".join(lines)

    lines.append(f"📋 {len(plans)} setup(s) from NSE volume gainers")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━\n")

    for i, plan in enumerate(plans, 1):
        g     = plan["gainer"]
        stock = plan["stock"]
        trade = plan["trade"]
        news  = plan["news"]

        chg_icon = "🟢" if g["change_pct"] >= 0 else "🔴"
        bias     = stock["bias"]
        bias_ico = "📈" if bias == "LONG" else ("📉" if bias == "SHORT" else "➖")

        lines.append(f"*{i}. {g['symbol']}*  {bias_ico} {bias}")
        lines.append(
            f"   LTP ₹{g['ltp']}  {chg_icon} {g['change_pct']:+.2f}%"
            f"  |  Vol {g['volume_l']:.1f}L ({g['vol_x']:.1f}x avg)"
            f"  |  Value ₹{g['value_cr']:.0f} Cr"
        )

        lvl = stock["levels"]
        lines.append(
            f"   PDH ₹{lvl['pdh']}  PDL ₹{lvl['pdl']}  EMA20 ₹{lvl['ema']}"
            f" ({'above' if lvl['above_ema'] else 'below'})"
        )

        if trade["valid"]:
            lines.append(
                f"   🎯 Entry ₹{trade['entry']}  🛑 SL ₹{trade['stop_loss']}"
                f"  ({trade['sl_pct']}%)"
            )
            lines.append(
                f"   🏁 T1 ₹{trade['target1']}  🏆 T2 ₹{trade['target2']}"
                f"  | R:R 1:{trade['rr_ratio']}"
            )
            lines.append(
                f"   Qty {trade['shares']}  |  Capital ₹{trade['capital_required']}"
                f"  |  Risk ₹{trade['actual_risk']}"
            )
        else:
            lines.append(f"   ⛔ Skip — {trade['reason']}")

        lines.append("   *Why it's moving:*")
        lines.extend(_format_news(news))
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("_Momentum plays burn fast — confirm on 5-min chart, keep SL tight._")
    return "\n".join(lines)


def run_momentum_job() -> None:
    log.info("▶ Momentum job started")
    try:
        rows = fetch_nse_volume_gainers()
        gainers = filter_top_gainers(rows)
        log.info(f"After filter: {len(gainers)} gainers")

        plans = []
        for g in gainers:
            stock = _build_stock_dict(g)
            if stock is None:
                continue
            trade = calculate_trade_levels(stock)
            news  = fetch_news_headlines(g["symbol"])
            plans.append({"gainer": g, "stock": stock, "trade": trade, "news": news})

        text = _format_momentum_brief(plans)
        ok = send_message(text)
        log.info("✅ Momentum brief sent" if ok else "❌ Telegram send failed")

    except Exception as e:
        log.error(f"Momentum job failed: {e}", exc_info=True)
        send_message(format_error_alert("momentum_job", str(e)))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_momentum_job()
