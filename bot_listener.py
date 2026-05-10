# bot_listener.py
# ─────────────────────────────────────────────────────────────
# On-demand Telegram bot. Lets you request a brief any time
# by sending a command in chat:
#   /brief or /night  → run the night screener + brief now
#   /morning          → run the morning brief now
#   /ping             → quick health check
#   /help             → list commands
# Only the configured TELEGRAM_CHAT_ID is allowed to trigger jobs.
# ─────────────────────────────────────────────────────────────

import asyncio
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from night_job import run_night_job
from morning_job import run_morning_job
from screener import run_screener
from brief_renderer import render_night_brief_png, build_short_caption
from telegram_sender import send_photo

log = logging.getLogger(__name__)

# Strip whitespace/quotes that sometimes sneak into env vars
_AUTHORIZED_CHAT_ID = str(TELEGRAM_CHAT_ID).strip().strip('"').strip("'")

HELP_TEXT = (
    "*Trader Assistant — On-Demand*\n\n"
    "/brief — run night brief now (text)\n"
    "/brief\\_png — run night brief now (PNG image)\n"
    "/night — same as /brief\n"
    "/morning — run morning brief now\n"
    "/ping — health check\n"
    "/help — this message\n\n"
    "_Scheduled runs continue automatically:_\n"
    "_Night 8:00 PM IST · Morning 8:45 AM IST_"
)


def _incoming_chat_id(update: Update) -> str | None:
    if update.effective_chat is None:
        return None
    return str(update.effective_chat.id)


def _is_authorized(update: Update) -> bool:
    incoming = _incoming_chat_id(update)
    if incoming is None:
        return False
    ok = incoming == _AUTHORIZED_CHAT_ID
    if not ok:
        log.warning(
            "Unauthorized update — incoming chat_id=%r, expected=%r",
            incoming, _AUTHORIZED_CHAT_ID,
        )
    return ok


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log.info("/help received from chat_id=%s", _incoming_chat_id(update))
    if not _is_authorized(update):
        return
    await update.message.reply_markdown(HELP_TEXT)


async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log.info("/ping received from chat_id=%s", _incoming_chat_id(update))
    if not _is_authorized(update):
        return
    await update.message.reply_text("pong ✅")


async def _run_blocking(fn):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, fn)


async def night_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log.info("/brief received from chat_id=%s", _incoming_chat_id(update))
    if not _is_authorized(update):
        return
    await update.message.reply_text("⏳ Running night brief — usually ~1–2 min…")
    await _run_blocking(run_night_job)


def _run_brief_png():
    """Blocking: screener → render PNG → send via Telegram."""
    watchlist = run_screener()
    png_bytes = render_night_brief_png(watchlist)
    caption   = build_short_caption(watchlist)
    send_photo(png_bytes, caption=caption)


async def brief_png_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log.info("/brief_png received from chat_id=%s", _incoming_chat_id(update))
    if not _is_authorized(update):
        return
    await update.message.reply_text("⏳ Building PNG brief — usually ~1–2 min…")
    await _run_blocking(_run_brief_png)


async def morning_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log.info("/morning received from chat_id=%s", _incoming_chat_id(update))
    if not _is_authorized(update):
        return
    await update.message.reply_text("⏳ Running morning brief — usually ~1–2 min…")
    await _run_blocking(run_morning_job)


async def log_any(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Logs every incoming message that wasn't caught by a command handler."""
    msg = update.message.text if update.message else None
    log.info("Update — chat_id=%s text=%r", _incoming_chat_id(update), msg)


def build_application() -> Application:
    log.info("Bot listener starting. Authorized chat_id=%r", _AUTHORIZED_CHAT_ID)
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler(["start", "help"], help_cmd))
    app.add_handler(CommandHandler("ping", ping_cmd))
    app.add_handler(CommandHandler(["brief", "night"], night_cmd))
    app.add_handler(CommandHandler("brief_png", brief_png_cmd))
    app.add_handler(CommandHandler("morning", morning_cmd))
    # Catch-all so we can confirm messages are reaching the bot
    app.add_handler(MessageHandler(filters.ALL, log_any))
    return app
