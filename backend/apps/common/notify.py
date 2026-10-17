from . import telegram


def notify_user(user, text) -> bool:
    """Send a Telegram message to a user if their bot is linked. Never raises."""
    chat_id = getattr(user, "telegram_chat_id", None)
    if not chat_id:
        return False
    ok, _ = telegram.safe_send(chat_id, text)
    return ok
