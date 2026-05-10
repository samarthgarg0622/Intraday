# config.py
# ─────────────────────────────────────────────────────────────
# TRADER ASSISTANT — CONFIGURATION
# Edit this file with your own values before running.
# ─────────────────────────────────────────────────────────────

import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────────────
# Get your bot token from @BotFather on Telegram
# Get your chat ID by messaging @userinfobot on Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "YOUR_CHAT_ID_HERE")

# ── Screening Filters ─────────────────────────────────────────
MIN_PRICE           = 100       # Minimum stock price in ₹
MAX_PRICE           = 3000      # Maximum stock price in ₹
MIN_VOLUME_RATIO    = 1.5       # Today's volume must be Nx the 20-day avg
MIN_PRICE_MOVE_PCT  = 1.5       # Minimum % price move to qualify
NEAR_LEVEL_PCT      = 0.8       # % proximity to S/R to be "near a level"
MAX_WATCHLIST_SIZE  = 5         # Max stocks in nightly watchlist

# ── S/R Level Settings ────────────────────────────────────────
SR_LOOKBACK_DAYS    = 60        # Days to look back for S/R zones
SR_ZONE_TOLERANCE   = 0.5       # % tolerance to cluster nearby levels
EMA_PERIOD          = 20        # EMA period (20-day)

# ── Capital & Risk ───────────────────────────────────────────
CAPITAL             = 100000  # Your total trading capital in ₹ — UPDATE THIS
MAX_RISK_PER_TRADE  = 0.015   # Max 1.5% of capital at risk per trade
DAILY_LOSS_LIMIT    = 0.02    # Stop trading for the day if loss > 2%

# ── Scheduling (IST times) ────────────────────────────────────
NIGHT_JOB_HOUR      = 20        # 8:00 PM IST
NIGHT_JOB_MINUTE    = 0
MORNING_JOB_HOUR    = 8         # 8:45 AM IST
MORNING_JOB_MINUTE  = 45

# ── NSE Nifty 200 Universe ────────────────────────────────────
# Liquid Nifty 200 stocks — yfinance requires ".NS" suffix for NSE
STOCK_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "HCLTECH.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "BAJFINANCE.NS", "WIPRO.NS",
    "NESTLEIND.NS", "TECHM.NS", "POWERGRID.NS", "NTPC.NS", "ONGC.NS",
    "TATAMOTORS.NS", "TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "COALINDIA.NS",
    "BAJAJFINSV.NS", "ADANIENT.NS", "ADANIPORTS.NS", "DIVISLAB.NS", "DRREDDY.NS",
    "CIPLA.NS", "EICHERMOT.NS", "HEROMOTOCO.NS", "BPCL.NS", "GRASIM.NS",
    "INDUSINDBK.NS", "M&M.NS", "BRITANNIA.NS", "APOLLOHOSP.NS", "TATACONSUM.NS",
    "SBILIFE.NS", "HDFCLIFE.NS", "BAJAJ-AUTO.NS", "UPL.NS", "SHREECEM.NS",
    "PIDILITIND.NS", "DABUR.NS", "GODREJCP.NS", "BERGEPAINT.NS", "HAVELLS.NS",
    "VOLTAS.NS", "MUTHOOTFIN.NS", "LUPIN.NS", "TORNTPHARM.NS", "COLPAL.NS",
    "BANDHANBNK.NS", "PNB.NS", "BANKBARODA.NS", "CANBK.NS", "IDFCFIRSTB.NS",
    "FEDERALBNK.NS", "NAUKRI.NS", "PERSISTENT.NS", "MPHASIS.NS", "LTIM.NS",
    "COFORGE.NS", "OFSS.NS", "TATACOMM.NS", "DLF.NS", "GODREJPROP.NS",
    "OBEROIRLTY.NS", "PRESTIGE.NS", "SAIL.NS", "NMDC.NS", "NATIONALUM.NS",
    "VEDL.NS", "HINDZINC.NS", "GAIL.NS", "IOC.NS", "HPCL.NS",
    "MOTHERSON.NS", "BALKRISIND.NS", "MRF.NS", "APOLLOTYRE.NS", "EXIDEIND.NS",
    "AUROPHARMA.NS", "BIOCON.NS", "GLENMARK.NS", "IPCALAB.NS", "ALKEM.NS",
    "CHOLAFIN.NS", "M&MFIN.NS", "MANAPPURAM.NS", "ABCAPITAL.NS", "LICHOUSFIN.NS",
    "NIFTYBEES.NS", "BANKBEES.NS", "ICICIB22.NS",   # ETFs
]
