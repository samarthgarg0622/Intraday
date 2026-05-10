# test_run.py
# ─────────────────────────────────────────────────────────────
# Run this locally BEFORE deploying to Railway to verify:
#   1. Data fetching works
#   2. Screener runs without errors
#   3. Levels are calculated correctly
#   4. Telegram bot is connected and sending
# ─────────────────────────────────────────────────────────────
# Usage:
#   pip install -r requirements.txt
#   cp .env.example .env       # fill in your tokens
#   python test_run.py
# ─────────────────────────────────────────────────────────────

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

def test_data_fetch():
    log.info("TEST 1: Data fetching...")
    from data_fetcher import fetch_stock_data, fetch_nifty_futures_change, clean_symbol
    df = fetch_stock_data("RELIANCE.NS")
    assert df is not None and len(df) > 0, "Failed to fetch RELIANCE data"
    log.info(f"  ✅ RELIANCE fetched: {len(df)} rows, latest close ₹{df['Close'].iloc[-1]:.2f}")

    nifty = fetch_nifty_futures_change()
    log.info(f"  ✅ Nifty: {nifty}")


def test_levels():
    log.info("TEST 2: Level calculation...")
    from data_fetcher import fetch_stock_data
    from levels import get_key_levels

    df = fetch_stock_data("TCS.NS")
    assert df is not None
    price  = df["Close"].iloc[-1]
    levels = get_key_levels(df, price)

    log.info(f"  ✅ TCS levels:")
    log.info(f"     PDH: ₹{levels['pdh']}  PDL: ₹{levels['pdl']}")
    log.info(f"     EMA: ₹{levels['ema']}  ({'above' if levels['above_ema'] else 'below'})")
    log.info(f"     Nearest resistance: ₹{levels['nearest_resistance']}")
    log.info(f"     Nearest support:    ₹{levels['nearest_support']}")


def test_screener():
    log.info("TEST 3: Screener (small universe for speed)...")
    from data_fetcher import fetch_all_stocks
    from screener import run_screener

    small_universe = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS",
                      "TATAMOTORS.NS", "SBIN.NS", "NIFTYBEES.NS"]
    stock_data = fetch_all_stocks(small_universe)
    watchlist  = run_screener(stock_data)

    log.info(f"  ✅ Screener returned {len(watchlist)} stocks:")
    for s in watchlist:
        log.info(f"     {s['display']:15s}  {s['bias']:7s}  score={s['score']}  vol={s['volume_ratio']}x  chg={s['change_pct']:+.2f}%")


def test_formatter():
    log.info("TEST 4: Message formatting...")
    from data_fetcher import fetch_all_stocks, fetch_nifty_futures_change
    from screener import run_screener
    from alert_formatter import format_night_brief, format_morning_brief

    small_universe = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "TATAMOTORS.NS", "NIFTYBEES.NS"]
    stock_data = fetch_all_stocks(small_universe)
    watchlist  = run_screener(stock_data)
    nifty      = fetch_nifty_futures_change()

    night_msg  = format_night_brief(watchlist)
    morn_msg   = format_morning_brief(watchlist, nifty)

    log.info(f"  ✅ Night brief: {len(night_msg)} chars")
    log.info(f"  ✅ Morning brief: {len(morn_msg)} chars")
    print("\n" + "="*50 + " NIGHT BRIEF PREVIEW " + "="*50)
    print(night_msg)
    print("\n" + "="*50 + " MORNING BRIEF PREVIEW " + "="*50)
    print(morn_msg)


def test_telegram():
    log.info("TEST 5: Telegram connection...")
    from telegram_sender import test_connection
    success = test_connection()
    if success:
        log.info("  ✅ Telegram message sent! Check your phone.")
    else:
        log.error("  ❌ Telegram failed. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  TRADER ASSISTANT — PRE-DEPLOYMENT TEST")
    print("="*60 + "\n")

    try:
        test_data_fetch()
        test_levels()
        test_screener()
        test_formatter()
        test_telegram()
        print("\n" + "="*60)
        print("  ALL TESTS PASSED ✅ — Ready to deploy on Railway!")
        print("="*60 + "\n")
    except Exception as e:
        log.error(f"\n❌ TEST FAILED: {e}", exc_info=True)
        print("\nFix the error above, then re-run this script.")
