"""Background loop: keeps weather, satellite hotspots and risk scores fresh.

Run it next to the API:  python manage.py run_worker
(or use `--once` from cron / systemd timers).
"""
import logging
import time

from django.core.management.base import BaseCommand

from apps.geo.models import Village
from apps.risk import engine, firms, weather

log = logging.getLogger("worker")


def job_weather():
    for v in Village.objects.all():
        if weather.weather_is_fresh(v):
            continue
        try:
            weather.refresh_weather(v)
        except weather.WeatherError as exc:
            log.warning("weather %s: %s", v.slug, exc)


def job_firms():
    try:
        total, created = firms.refresh_hotspots()
        log.info("firms: %s received, %s new", total, created)
    except firms.FirmsError as exc:
        log.warning("firms: %s", exc)


def job_engine():
    engine.evaluate_all()


class Command(BaseCommand):
    help = "Run the background worker (weather, FIRMS, risk engine)."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run every job once and exit")
        parser.add_argument("--engine-interval", type=int, default=60)
        parser.add_argument("--weather-interval", type=int, default=600)
        parser.add_argument("--firms-interval", type=int, default=900)

    def handle(self, *args, **opts):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
        jobs = [
            ("weather", job_weather, opts["weather_interval"]),
            ("firms", job_firms, opts["firms_interval"]),
            ("engine", job_engine, opts["engine_interval"]),  # last: uses fresh weather/hotspots
        ]
        if opts["once"]:
            for name, fn, _ in jobs:
                self._run(name, fn)
            return
        due = {name: 0.0 for name, _, _ in jobs}
        self.stdout.write("Worker started (Ctrl+C to stop).")
        try:
            while True:
                now = time.monotonic()
                for name, fn, interval in jobs:
                    if now >= due[name]:
                        self._run(name, fn)
                        due[name] = time.monotonic() + interval
                time.sleep(5)
        except KeyboardInterrupt:
            self.stdout.write("Worker stopped.")

    def _run(self, name, fn):
        try:
            fn()
        except Exception:  # keep the loop alive whatever one job does
            log.exception("job %s failed", name)
