# brief_renderer.py
# ─────────────────────────────────────────────────────────────
# Renders the night brief watchlist as a PNG image table.
# Used by the /brief_png on-demand command.
# ─────────────────────────────────────────────────────────────

import io
from datetime import datetime
import pytz

import matplotlib
matplotlib.use("Agg")  # headless backend (Railway/Linux server)
import matplotlib.pyplot as plt

from trade_calculator import calculate_trade_levels

IST = pytz.timezone("Asia/Kolkata")

# Colors
HEADER_BG    = "#1f2937"   # slate-800
HEADER_FG    = "#ffffff"
LONG_BG      = "#d1fae5"   # emerald-100
SHORT_BG     = "#fee2e2"   # red-100
SKIP_BG      = "#e5e7eb"   # gray-200
ALT_TINT     = "#f9fafb"   # very light gray for header alt


def _date_str() -> str:
    return datetime.now(IST).strftime("%a, %d %b %Y")


def _render_table_png(title: str, subtitle: str, headers: list,
                      rows: list, row_colors: list,
                      footer: str) -> bytes:
    """Generic table-to-PNG renderer used by night/morning briefs."""
    n_rows = len(rows)
    n_cols = len(headers)

    fig_w = 13
    fig_h = 1.6 + n_rows * 0.55
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
    ax.axis("off")

    fig.suptitle(title, fontsize=16, fontweight="bold", y=0.98)
    fig.text(0.5, 0.93, subtitle, ha="center", fontsize=11, color="#4b5563")

    table = ax.table(
        cellText=rows,
        colLabels=headers,
        cellColours=row_colors,
        colColours=[HEADER_BG] * n_cols,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.7)

    for j in range(n_cols):
        cell = table[(0, j)]
        cell.set_text_props(color=HEADER_FG, fontweight="bold")
        cell.set_edgecolor(HEADER_BG)

    for i in range(1, n_rows + 1):
        for j in range(n_cols):
            cell = table[(i, j)]
            cell.set_edgecolor("#cbd5e1")
            if j == 2 or j == n_cols - 1:  # Bias + Status bold
                cell.set_text_props(fontweight="bold")

    fig.text(0.5, 0.02, footer, ha="center",
             fontsize=9, color="#6b7280", style="italic")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def render_night_brief_png(watchlist: list) -> bytes:
    """Returns PNG bytes for the night brief watchlist."""
    date_str = _date_str()

    if not watchlist:
        return _render_empty_png(f"NIGHT BRIEF — {date_str}")

    headers = ["#", "Symbol", "Bias", "Close", "Chg%", "Vol",
               "Entry", "SL", "T1", "T2", "Qty", "R:R", "Status"]

    rows         = []
    row_colors   = []

    for i, stock in enumerate(watchlist, 1):
        trade = calculate_trade_levels(stock)
        sym   = stock["display"]
        bias  = stock["bias"]
        price = stock["price"]
        chg   = stock["change_pct"]
        vol   = stock["volume_ratio"]

        if trade["valid"]:
            row = [
                str(i), sym, bias,
                f"₹{price:g}",
                f"{chg:+.2f}%",
                f"{vol}x",
                f"₹{trade['entry']:g}",
                f"₹{trade['stop_loss']:g}",
                f"₹{trade['target1']:g}",
                f"₹{trade['target2']:g}",
                str(trade["shares"]),
                f"1:{trade['rr_ratio']}",
                "GO",
            ]
            bg = LONG_BG if bias == "LONG" else SHORT_BG
        else:
            row = [
                str(i), sym, bias,
                f"₹{price:g}",
                f"{chg:+.2f}%",
                f"{vol}x",
                f"₹{trade['entry']:g}",
                "—", "—", "—", "—", "—",
                "SKIP",
            ]
            bg = SKIP_BG

        rows.append(row)
        row_colors.append([bg] * len(headers))

    valid_count = sum(1 for r in rows if r[-1] == "GO")
    skip_count  = len(rows) - valid_count

    return _render_table_png(
        title=f"NIGHT BRIEF — {date_str}",
        subtitle=f"Watchlist: {len(rows)}   ·   Tradeable: {valid_count}   ·   Skip: {skip_count}",
        headers=headers,
        rows=rows,
        row_colors=row_colors,
        footer="Wait for 9:30 AM · 5-min candle confirmation · SL immediately after fill · Exit by 3:20 PM",
    )


def render_morning_brief_png(watchlist: list, nifty: dict) -> bytes:
    """Returns PNG bytes for the morning brief — same table shape with
    GO / COUNTER / SKIP status based on Nifty alignment."""
    date_str = _date_str()
    chg      = nifty.get("change_pct", 0)
    direction= nifty.get("direction", "")
    close    = nifty.get("close", 0)

    if not watchlist:
        return _render_empty_png(f"MORNING BRIEF — {date_str}")

    nifty_bullish = chg >= 0

    headers = ["#", "Symbol", "Bias", "Entry", "SL",
               "T1", "T2", "Qty", "R:R", "Status"]

    rows       = []
    row_colors = []

    for i, stock in enumerate(watchlist, 1):
        trade = calculate_trade_levels(stock)
        sym   = stock["display"]
        bias  = stock["bias"]

        aligned = (bias == "LONG" and nifty_bullish) or \
                  (bias == "SHORT" and not nifty_bullish) or \
                  bias == "NEUTRAL"

        if not trade["valid"]:
            status = "SKIP"
            bg     = SKIP_BG
            row = [str(i), sym, bias, f"₹{trade['entry']:g}",
                   "—", "—", "—", "—", "—", status]
        else:
            if aligned:
                status = "GO"
                bg     = LONG_BG if bias == "LONG" else SHORT_BG
            else:
                status = "COUNTER"
                bg     = SKIP_BG
            row = [
                str(i), sym, bias,
                f"₹{trade['entry']:g}",
                f"₹{trade['stop_loss']:g}",
                f"₹{trade['target1']:g}",
                f"₹{trade['target2']:g}",
                str(trade["shares"]),
                f"1:{trade['rr_ratio']}",
                status,
            ]

        rows.append(row)
        row_colors.append([bg] * len(headers))

    go_count    = sum(1 for r in rows if r[-1] == "GO")
    counter_cnt = sum(1 for r in rows if r[-1] == "COUNTER")
    skip_cnt    = sum(1 for r in rows if r[-1] == "SKIP")

    sign = "+" if chg >= 0 else ""
    subtitle = (f"Nifty 50: ₹{close}  {direction}  ({sign}{chg:.2f}%)   ·   "
                f"GO: {go_count}  ·  Counter: {counter_cnt}  ·  Skip: {skip_cnt}")

    return _render_table_png(
        title=f"MORNING BRIEF — {date_str}",
        subtitle=subtitle,
        headers=headers,
        rows=rows,
        row_colors=row_colors,
        footer="Observe 9:15–9:30 · Set GTT only if level still valid on chart · Max ₹1,500 risk per trade",
    )


def _render_empty_png(title: str) -> bytes:
    fig, ax = plt.subplots(figsize=(8, 3), dpi=150)
    ax.axis("off")
    ax.text(0.5, 0.7, title,
            ha="center", fontsize=15, fontweight="bold")
    ax.text(0.5, 0.45, "No strong setups found today.",
            ha="center", fontsize=12)
    ax.text(0.5, 0.25, "Capital protection first — consider sitting out.",
            ha="center", fontsize=10, color="#6b7280", style="italic")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def build_short_caption(watchlist: list, title: str = "Night brief") -> str:
    """Short caption (under 1024 chars) — used as the photo caption.
    Lists GTT for tradeable setups only; full text is sent as a follow-up
    message."""
    if not watchlist:
        return f"{title} · {_date_str()}\nNo setups today."

    lines = [f"{title} · {_date_str()}", ""]
    valid = []
    for stock in watchlist:
        trade = calculate_trade_levels(stock)
        if trade["valid"]:
            valid.append((stock["display"], stock["bias"], trade))

    if not valid:
        lines.append("All setups screened SKIP — see image for reasons.")
        return "\n".join(lines)

    lines.append(f"GTT plan — {len(valid)} tradeable:")
    for sym, bias, trade in valid:
        action = "Buy" if bias == "LONG" else "Sell"
        lines.append(
            f"• {sym} {bias}: trigger ₹{trade['trigger_level']:g}, "
            f"{action.lower()} {trade['shares']} @ ₹{trade['entry']:g}, "
            f"SL ₹{trade['stop_loss']:g}, T1 ₹{trade['target1']:g}"
        )

    text = "\n".join(lines)
    if len(text) > 1020:
        text = text[:1017] + "…"
    return text
