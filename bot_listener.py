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
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from night_job import run_night_job
from morning_job import run_morning_job

log = logging.getLogger(__name__)

HELP_TEXT = (
    "*Trader Assistant — On-Demand*\n\n"
    "/brief — run night brief now\n"
    "/night — same as /brief\n"
    "/morning — run morning brief now\n"
    "/ping — health check\n"
    "/help — this message\n\n"
    "_Scheduled runs continue automatically:_\n"
    "_Night 8:00 PM IST · Morning 8:45 AM IST_"
)


def _is_authorized(update: Update) -> bool:
    return update.effective_chat is not None and \
           str(update.effective_chat.id) == str(TELEGRAM_CHAT_ID)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    await update.message.reply_markdown(HELP_TEXT)


async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    await update.message.reply_text("pong ✅")


async def _run_blocking(fn):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, fn)


async def night_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    await update.message.reply_text("⏳ Running night brief — usually ~1–2 min…")
    log.info("On-demand /brief triggered")
    await _run_blocking(run_night_job)


async def morning_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    await update.message.reply_text("⏳ Running morning brief — usually ~1–2 min…")
    log.info("On-demand /morning triggered")
    await _run_blocking(run_morning_job)


def build_application() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler(["start", "help"], help_cmd))
    app.add_handler(CommandHandler("ping", ping_cmd))
    app.add_handler(CommandHandler(["brief", "night"], night_cmd))
    app.add_handler(CommandHandler("morning", morning_cmd))
    return app
