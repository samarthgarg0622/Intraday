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
from telegram_sender import send_message
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

        # Load night state and compare
        night_state  = load_night_state()
        comparison   = compare_watchlists(night_state, morning_watchlist) \
                       if night_state else None

        message = format_morning_brief(morning_watchlist, nifty, comparison)
        success = send_message(message)

        if success:
            log.info("✅ Morning brief sent successfully")
        else:
            log.error("❌ Failed to send morning brief")

    except Exception as e:
        log.error(f"Morning job failed: {e}", exc_info=True)
        send_message(format_error_alert("morning_job", str(e)))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_morning_job()
