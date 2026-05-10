# morning_job.py
# ─────────────────────────────────────────────────────────────
# Runs at 8:45 AM IST every weekday
# Re-fetches watchlist, compares with night brief, sends morning update
# Explicitly calls out any changes since last night
# ─────────────────────────────────────────────────────────────

import logging
from screener import run_screener
from data_fetcher import fetch_nifty_futures_change
from alert_formatter import format_morning_brief, format_error_alert
from brief_renderer import render_morning_brief_png, build_short_caption
from telegram_sender import send_message, send_photo
from state import load_night_state, compare_watchlists

log = logging.getLogger(__name__)


def run_morning_job():
    log.info("▶ Morning job started")

    try:
        log.info("Fetching Nifty data...")
        nifty = fetch_nifty_futures_change()
        log.info(f"Nifty: {nifty}")

        log.info("Running morning screener...")
        morning_watchlist = run_screener()
        log.info(f"Morning watchlist: {len(morning_watchlist)} stocks")

        night_state  = load_night_state()
        comparison   = compare_watchlists(night_state, morning_watchlist) \
                       if night_state else None

        png     = render_morning_brief_png(morning_watchlist, nifty)
        caption = build_short_caption(morning_watchlist, title="Morning brief")
        text    = format_morning_brief(morning_watchlist, nifty, comparison)

        photo_ok = send_photo(png, caption=caption)
        text_ok  = send_message(text)

        if photo_ok and text_ok:
            log.info("✅ Morning brief sent (PNG + text)")
        else:
            log.error(f"❌ Morning brief partial failure (photo={photo_ok}, text={text_ok})")

    except Exception as e:
        log.error(f"Morning job failed: {e}", exc_info=True)
        send_message(format_error_alert("morning_job", str(e)))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_morning_job()
