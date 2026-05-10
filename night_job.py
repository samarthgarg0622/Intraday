# night_job.py
# ─────────────────────────────────────────────────────────────
# Runs at 8:00 PM IST every weekday
# Screens stocks, calculates levels, sends night brief
# Saves state to disk for morning comparison
# ─────────────────────────────────────────────────────────────

import logging
from screener import run_screener
from alert_formatter import format_night_brief, format_error_alert
from brief_renderer import render_night_brief_png, build_short_caption
from telegram_sender import send_message, send_photo
from state import save_night_state

log = logging.getLogger(__name__)


def run_night_job():
    log.info("▶ Night job started")

    try:
        log.info("Running stock screener...")
        watchlist = run_screener()
        log.info(f"Screener returned {len(watchlist)} stocks")

        save_night_state(watchlist)

        png     = render_night_brief_png(watchlist)
        caption = build_short_caption(watchlist, title="Night brief")
        text    = format_night_brief(watchlist)

        photo_ok = send_photo(png, caption=caption)
        text_ok  = send_message(text)

        if photo_ok and text_ok:
            log.info("✅ Night brief sent (PNG + text)")
        else:
            log.error(f"❌ Night brief partial failure (photo={photo_ok}, text={text_ok})")

    except Exception as e:
        log.error(f"Night job failed: {e}", exc_info=True)
        send_message(format_error_alert("night_job", str(e)))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_night_job()
