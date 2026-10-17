"""Simulate a mudflow rolling down a village's river, straight through the database.

For the live hardware-style demo use scripts/simulate_node.py (HTTP). This command is the
quick way to test the whole chain: events -> risk engine -> alert -> Telegram -> siren.
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.alerts.models import Alert
from apps.alerts.services import resolve_alert
from apps.common.geo import haversine_km
from apps.geo.models import Village
from apps.risk.engine import evaluate_village
from apps.sensors.models import Node, VibrationEvent


class Command(BaseCommand):
    help = "Simulate a mudflow passing the upstream nodes of a village."

    def add_arguments(self, parser):
        parser.add_argument("--village", default="ak-tash", help="Village slug (default: ak-tash)")
        parser.add_argument("--speed-kmh", type=float, default=25.0, help="Mudflow front speed")
        parser.add_argument("--nodes", type=int, default=2, help="How many upstream nodes have already triggered")
        parser.add_argument("--reset", action="store_true", help="Clear simulated events and resolve active alerts")

    def handle(self, *args, **opts):
        try:
            village = Village.objects.get(slug=opts["village"])
        except Village.DoesNotExist:
            raise CommandError("Unknown village. Run `python manage.py seed_demo` first.") from None
        nodes = list(
            Node.objects.filter(village=village, is_active=True, kind__in=[Node.MULTI, Node.GEOPHONE]).order_by("flow_order")
        )
        if len(nodes) < 1:
            raise CommandError("No geophone nodes in this village.")

        if opts["reset"]:
            VibrationEvent.objects.filter(node__in=nodes).delete()
            for alert in Alert.objects.filter(village=village, status=Alert.ACTIVE):
                resolve_alert(alert, Alert.RESOLVED)
            evaluate_village(village, notify=False)
            self.stdout.write(self.style.SUCCESS("Reset done."))
            return

        n = max(1, min(opts["nodes"], len(nodes)))
        now = timezone.now()
        # Place events in the past so that the front moved at the requested speed between nodes.
        times = [now]
        for i in range(n - 1, 0, -1):
            d = haversine_km(nodes[i - 1].lat, nodes[i - 1].lon, nodes[i].lat, nodes[i].lon) * settings.PATH_FACTOR
            times.insert(0, times[0] - timedelta(hours=d / opts["speed_kmh"]))
        for node, t in zip(nodes[:n], times):
            for k, rms in enumerate((0.45, 0.80, 1.20)):
                e = VibrationEvent.objects.create(
                    node=node, classification="mudflow", confidence=0.9, rms=rms, dominant_freq_hz=25.0,
                    features={"simulated": True},
                )
                VibrationEvent.objects.filter(pk=e.pk).update(created_at=t + timedelta(seconds=k * 2))

        results = evaluate_village(village, now=now)
        for r in results:
            if r.hazard == "mudflow":
                eta = "-" if r.eta_seconds is None else f"{r.eta_seconds // 60} min {r.eta_seconds % 60} s"
                self.stdout.write(self.style.SUCCESS(f"mudflow: {r.level} (score {r.score:.0f}), ETA {eta}"))
                for reason in r.reasons:
                    self.stdout.write(f"  - {reason}")
        self.stdout.write("Check /api/alerts/active/ and your Telegram. Use --reset between runs.")
