from django.core.management.base import BaseCommand, CommandError

from apps.risk import firms


class Command(BaseCommand):
    help = "Download recent NASA FIRMS fire hotspots for Kyrgyzstan into the database."

    def handle(self, *args, **options):
        try:
            total, created = firms.refresh_hotspots()
        except firms.FirmsError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(self.style.SUCCESS(f"FIRMS: {total} hotspots received, {created} new."))
