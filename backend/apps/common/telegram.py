"""Minimal Telegram Bot API client (plain `requests`, no extra dependency).

Never log the request URL: it contains the bot token.
"""
import logging

import requests
from django.conf import settings

log = logging.getLogger(__name__)

API_ROOT = "https://api.telegram.org"
MAX_FILE_BYTES = 10 * 1024 * 1024


class TelegramError(Exception):
    pass


def is_configured() -> bool:
    return bool(settings.TELEGRAM_BOT_TOKEN)


def call(method, payload=None, files=None, timeout=15):
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise TelegramError("TELEGRAM_BOT_TOKEN is not set")
    url = f"{API_ROOT}/bot{token}/{method}"
    try:
        if files:
            resp = requests.post(url, data=payload or {}, files=files, timeout=timeout)
        else:
            resp = requests.post(url, json=payload or {}, timeout=timeout)
    except requests.RequestException as exc:
        # Do not chain the exception: its message would contain the URL (and the token).
        raise TelegramError(f"{method}: network error ({exc.__class__.__name__})") from None
    try:
        data = resp.json()
    except ValueError:
        raise TelegramError(f"{method}: HTTP {resp.status_code}, invalid response") from None
    if not data.get("ok"):
        raise TelegramError(f"{method}: {data.get('description', resp.status_code)}")
    return data["result"]


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return call("sendMessage", payload)


def send_location(chat_id, lat, lon):
    return call("sendLocation", {"chat_id": chat_id, "latitude": lat, "longitude": lon})


def answer_callback(callback_id, text=""):
    return call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})


def get_updates(offset=None, timeout=25):
    payload = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
    if offset is not None:
        payload["offset"] = offset
    return call("getUpdates", payload, timeout=timeout + 10)


def get_file_bytes(file_id):
    info = call("getFile", {"file_id": file_id})
    if info.get("file_size", 0) > MAX_FILE_BYTES:
        raise TelegramError("file too large")
    url = f"{API_ROOT}/file/bot{settings.TELEGRAM_BOT_TOKEN}/{info['file_path']}"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise TelegramError(f"download failed ({exc.__class__.__name__})") from None
    return resp.content


def safe_send(chat_id, text, reply_markup=None):
    """Send a message; return (ok, error_text). Never raises."""
    if not chat_id:
        return False, "no chat id"
    try:
        send_message(chat_id, text, reply_markup)
        return True, ""
    except TelegramError as exc:
        log.warning("telegram send failed: %s", exc)
        return False, str(exc)[:200]
