# scheduler.py
# ─────────────────────────────────────────────────────────────
# Main entry point. Runs the APScheduler with IST timezone.
# Weekdays only: Night job 8PM, Morning job 8:45AM
# Deploy this on Railway — it runs 24/7.
# ─────────────────────────────────────────────────────────────

import logging
import time
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from night_job import run_night_job
from morning_job import run_morning_job
from config import (
    NIGHT_JOB_HOUR, NIGHT_JOB_MINUTE,
    MORNING_JOB_HOUR, MORNING_JOB_MINUTE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


def main():
    scheduler = BlockingScheduler(timezone=IST)

    # ── Night Job: Mon–Fri at 8:00 PM IST ─────────────────────
    scheduler.add_job(
        run_night_job,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=NIGHT_JOB_HOUR,
            minute=NIGHT_JOB_MINUTE,
            timezone=IST,
        ),
        id="night_job",
        name="Nightly Watchlist & Levels",
        misfire_grace_time=300,   # Allow 5 min late start
    )

    # ── Morning Job: Mon–Fri at 8:45 AM IST ───────────────────
    scheduler.add_job(
        run_morning_job,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=MORNING_JOB_HOUR,
            minute=MORNING_JOB_MINUTE,
            timezone=IST,
        ),
        id="morning_job",
        name="Morning Brief & Gap Analysis",
        misfire_grace_time=300,
    )

    log.info("=" * 55)
    log.info("  TRADER ASSISTANT SCHEDULER STARTED")
    log.info(f"  Night brief:   Mon–Fri at {NIGHT_JOB_HOUR:02d}:{NIGHT_JOB_MINUTE:02d} IST")
    log.info(f"  Morning brief: Mon–Fri at {MORNING_JOB_HOUR:02d}:{MORNING_JOB_MINUTE:02d} IST")
    log.info("=" * 55)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
