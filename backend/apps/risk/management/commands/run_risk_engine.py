from django.core.management.base import BaseCommand

from apps.risk.engine import evaluate_all


class Command(BaseCommand):
    help = "Recompute risk for every village and sync alerts."

    def add_arguments(self, parser):
        parser.add_argument("--no-notify", action="store_true", help="Do not create or send alerts")

    def handle(self, *args, **options):
        for slug, results in evaluate_all(notify=not options["no_notify"]).items():
            summary = ", ".join(f"{r.hazard}={r.level}({r.score:.0f})" for r in results)
            self.stdout.write(f"{slug}: {summary}")
