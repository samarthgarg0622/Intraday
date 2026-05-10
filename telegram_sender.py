# telegram_sender.py
# ─────────────────────────────────────────────────────────────
# Sends messages via Telegram Bot API
# ─────────────────────────────────────────────────────────────

import requests
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

log = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message(text: str, parse_mode: str = "Markdown") -> bool:
    """
    Sends a text message to your Telegram chat.
    Returns True on success, False on failure.
    Telegram has a 4096 character limit per message — long messages are split.
    """
    chunks = _split_message(text, limit=4000)

    for chunk in chunks:
        try:
            resp = requests.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id":    TELEGRAM_CHAT_ID,
                    "text":       chunk,
                    "parse_mode": parse_mode,
                },
                timeout=10,
            )
            resp.raise_for_status()
            log.info(f"Telegram message sent ({len(chunk)} chars)")

        except requests.exceptions.RequestException as e:
            log.error(f"Failed to send Telegram message: {e}")
            return False

    return True


def _split_message(text: str, limit: int = 4000) -> list:
    """Splits a long message into chunks at newline boundaries."""
    if len(text) <= limit:
        return [text]

    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line + "\n"
        else:
            current += line + "\n"

    if current:
        chunks.append(current)

    return chunks


def send_photo(photo_bytes: bytes, caption: str = "",
               parse_mode: str = "Markdown",
               filename: str = "brief.png") -> bool:
    """
    Sends a photo to your Telegram chat.
    Caption max length is 1024 chars (Telegram limit) — truncated if longer.
    """
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/sendPhoto",
            data={
                "chat_id":    TELEGRAM_CHAT_ID,
                "caption":    caption[:1024],
                "parse_mode": parse_mode,
            },
            files={"photo": (filename, photo_bytes, "image/png")},
            timeout=30,
        )
        resp.raise_for_status()
        log.info(f"Telegram photo sent ({len(photo_bytes)} bytes, "
                 f"caption {len(caption)} chars)")
        return True

    except requests.exceptions.RequestException as e:
        log.error(f"Failed to send Telegram photo: {e}")
        return False


def test_connection() -> bool:
    """Sends a test message to verify bot token and chat ID are correct."""
    return send_message(
        "✅ *Trader Assistant connected!*\n"
        "Your nightly and morning alerts are active.\n\n"
        "_Night brief: 8:00 PM IST_\n"
        "_Morning brief: 8:45 AM IST_"
    )
