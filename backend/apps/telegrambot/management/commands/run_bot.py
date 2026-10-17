"""Telegram bot, long-polling. Run it next to the API:  python manage.py run_bot"""
import logging
import time

from django.core.management.base import BaseCommand, CommandError

from apps.common import telegram
from apps.telegrambot.handlers import handle_update
from apps.telegrambot.texts import BOT_COMMANDS

log = logging.getLogger("bot")


class Command(BaseCommand):
    help = "Run the Telegram bot using long polling."

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
        if not telegram.is_configured():
            raise CommandError("TELEGRAM_BOT_TOKEN is not set in .env")
        try:
            me = telegram.call("getMe")
            telegram.call("deleteWebhook")  # polling and webhooks cannot be used together
            telegram.call("setMyCommands", {"commands": BOT_COMMANDS})
        except telegram.TelegramError as exc:
            raise CommandError(f"Cannot reach Telegram: {exc}") from None
        self.stdout.write(self.style.SUCCESS(f"Bot @{me.get('username')} is running (Ctrl+C to stop)."))

        offset = None
        try:
            while True:
                try:
                    updates = telegram.get_updates(offset=offset, timeout=25)
                except telegram.TelegramError as exc:
                    log.warning("polling error: %s", exc)
                    time.sleep(5)
                    continue
                for update in updates:
                    offset = update["update_id"] + 1
                    try:
                        handle_update(update)
                    except Exception:  # one bad update must never stop the bot
                        log.exception("failed to handle update %s", update.get("update_id"))
        except KeyboardInterrupt:
            self.stdout.write("Bot stopped.")
