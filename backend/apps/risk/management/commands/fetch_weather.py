from django.core.management.base import BaseCommand

from apps.geo.models import Village
from apps.risk import weather


class Command(BaseCommand):
    help = "Fetch Open-Meteo weather for every village (skips villages with fresh data)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Ignore the cache window")

    def handle(self, *args, **options):
        ok = failed = 0
        for village in Village.objects.all():
            if not options["force"] and weather.weather_is_fresh(village):
                continue
            try:
                weather.refresh_weather(village)
                ok += 1
            except weather.WeatherError as exc:
                failed += 1
                self.stderr.write(f"{village.slug}: {exc}")
        self.stdout.write(f"Weather updated for {ok} villages, {failed} failed.")
