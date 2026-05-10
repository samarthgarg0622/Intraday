# 📈 Trader Assistant — NSE Intraday Screener

Automated nightly + morning alerts for NSE intraday equity/ETF trading.
Sends Telegram messages at **8:00 PM** (night brief) and **8:45 AM** (morning brief) every weekday.

---

## What It Does

**Night Brief (8:00 PM):**
- Screens Nifty 200 universe for stocks with volume surge + significant price move
- Calculates PDH, PDL, Support/Resistance zones, 20 EMA
- Determines LONG / SHORT bias
- Sends formatted Telegram message with top 5 setups

**Morning Brief (8:45 AM):**
- Re-checks watchlist with fresh data
- Checks Nifty 50 direction
- Flags gap ups/downs and alignment with Nifty trend
- Sends go/no-go brief for each setup

---

## Setup Instructions

### Step 1 — Create Your Telegram Bot (5 mins)

1. Open Telegram → search **@BotFather**
2. Send `/newbot` → follow prompts → give it a name like "MyTraderBot"
3. BotFather will send you a **Bot Token** — copy it (looks like `123456789:ABCdef...`)
4. Now search **@userinfobot** on Telegram
5. Send any message to it → it replies with your **Chat ID** (a number like `987654321`)
6. Start your new bot by searching its username and pressing **Start**

### Step 2 — Set Up Locally (Test First)

```bash
# Clone or download this folder
cd trader-assistant

# Install dependencies
pip install -r requirements.txt

# Create your .env file
cp .env.example .env

# Edit .env with your tokens
# TELEGRAM_BOT_TOKEN=your_token_here
# TELEGRAM_CHAT_ID=your_chat_id_here

# Run the test suite
python test_run.py
```

If all 5 tests pass and you receive a Telegram message — you're ready to deploy.

### Step 3 — Deploy on Railway (Free Hosting)

**Railway** keeps the scheduler running 24/7. Free tier is sufficient.

1. Go to [railway.app](https://railway.app) → sign up with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Push your `trader-assistant` folder to a GitHub repo first:
   ```bash
   git init
   git add .
   git commit -m "initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/trader-assistant.git
   git push -u origin main
   ```
4. In Railway: select your repo → Railway auto-detects Python
5. Go to **Variables** tab in Railway → add:
   - `TELEGRAM_BOT_TOKEN` = your token
   - `TELEGRAM_CHAT_ID`   = your chat ID
6. Railway reads the `Procfile` and runs `python scheduler.py`
7. Check **Logs** tab — you should see the scheduler started message

**That's it.** Railway keeps it running. You get alerts every weekday.

---

## Customising the Screener

All settings are in `config.py`:

| Setting | Default | What it does |
|---|---|---|
| `MIN_VOLUME_RATIO` | 1.5 | Stock volume must be 1.5× its 20-day average |
| `MIN_PRICE_MOVE_PCT` | 1.5 | Stock must have moved 1.5%+ today |
| `NEAR_LEVEL_PCT` | 0.8 | Stock within 0.8% of a key S/R level |
| `MAX_WATCHLIST_SIZE` | 5 | Max stocks in nightly brief |
| `SR_LOOKBACK_DAYS` | 60 | Days of history used to find S/R levels |
| `EMA_PERIOD` | 20 | EMA period for bias determination |
| `MIN_PRICE` | 100 | Minimum stock price in ₹ |
| `MAX_PRICE` | 3000 | Maximum stock price in ₹ |

To add/remove stocks from the universe, edit `STOCK_UNIVERSE` in `config.py`.

---

## On-Demand Briefs (from Telegram)

Once `scheduler.py` is running (locally or on Railway), send any of these
commands to your bot in Telegram to get a brief immediately:

| Command | What it does |
|---|---|
| `/brief` | Run the night screener + brief right now |
| `/night` | Same as `/brief` |
| `/morning` | Run the morning brief right now |
| `/ping` | Health check — bot replies `pong ✅` |
| `/help` | List available commands |

Only the `TELEGRAM_CHAT_ID` configured in env vars is allowed to trigger jobs.

## Running Jobs Manually

```bash
# Run just the night job right now
python night_job.py

# Run just the morning job right now
python morning_job.py

# Start the full scheduler + on-demand bot (runs continuously)
python scheduler.py
```

---

## File Structure

```
trader-assistant/
├── config.py            # All settings and stock universe
├── data_fetcher.py      # OHLCV data via yfinance
├── levels.py            # PDH/PDL, S/R zones, EMA calculation
├── screener.py          # 4-filter screening logic + bias
├── alert_formatter.py   # Night brief and morning brief formatter
├── telegram_sender.py   # Sends messages via Telegram Bot API
├── night_job.py         # Night job (screener + levels + alert)
├── morning_job.py       # Morning job (gap check + final brief)
├── scheduler.py         # APScheduler entry point (deploy this)
├── test_run.py          # Pre-deployment test suite
├── requirements.txt     # Python dependencies
├── Procfile             # Railway start command
└── .env.example         # Environment variable template
```

---

## Important Limitations

- **Data source:** yfinance (Yahoo Finance) — unofficial, free. Occasionally unreliable on holidays or after market restructuring. If data fails, you'll get an error Telegram message.
- **This is a screener, not a trading bot.** It does NOT place orders. All trades are your decision.
- **S/R levels are algorithmic.** Always verify on your Kite chart before trading. The code identifies zones — your eyes confirm.
- **No real-time data.** All analysis is based on end-of-day data. Intraday price action still requires your chart.

---

## Disclaimer

This tool is for educational and personal use only. It does not constitute financial advice. Always make your own trading decisions and use proper risk management.
