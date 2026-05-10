# night_job.py
# ─────────────────────────────────────────────────────────────
# Runs at 8:00 PM IST every weekday
# Screens stocks, calculates levels, sends night brief
# Saves state to disk for morning comparison
# ─────────────────────────────────────────────────────────────

import logging
from screener import run_screener
from alert_formatter import format_night_brief, format_error_alert
from telegram_sender import send_message
from state import save_night_state

log = logging.getLogger(__name__)


def run_night_job():
    log.info("▶ Night job started")

    try:
        log.info("Running stock screener...")
        watchlist = run_screener()
        log.info(f"Screener returned {len(watchlist)} stocks")

        # Save state for morning comparison
        save_night_state(watchlist)

        message = format_night_brief(watchlist)
        success = send_message(message)

        if success:
            log.info("✅ Night brief sent successfully")
        else:
            log.error("❌ Failed to send night brief")

    except Exception as e:
        log.error(f"Night job failed: {e}", exc_info=True)
        send_message(format_error_alert("night_job", str(e)))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_night_job()
